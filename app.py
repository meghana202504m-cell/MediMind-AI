import hashlib
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend.llm_provider import get_llm_provider
from backend.structured_store import (
    get_patient_history,
    get_patient_reports,
    get_report,
    list_reports,
    persist_report,
)
from rag.chunker import chunk_text
from rag.context_builder import build_context
from rag.embedder import create_embeddings
from rag.image_reader import extract_text_from_image, extract_text_from_scanned_pdf
from rag.llm import generate_answer
from rag.pdf_reader import read_pdf
from rag.question_router import route_question
from rag.retriever import retrieve_chunks
from rag.vector_store import store_chunks

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
REPORT_DIR = BASE_DIR / "data" / "reports"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
TEMP_IMAGE_DIR = BASE_DIR / "data" / "temp_images"
for directory in (REPORT_DIR, PROCESSED_DIR, TEMP_IMAGE_DIR):
    directory.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="MediMind AI",
    description="AI-powered preventive healthcare assistant with report analysis, history tracking, and trusted RAG.",
    version="1.1.0",
)

allowed_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://0.0.0.0:5173",
]
configured_origins = os.getenv("CORS_ORIGINS", "")
if configured_origins:
    allowed_origins.extend([origin.strip() for origin in configured_origins.split(',') if origin.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)
    document_id: str | None = None
    language: str = "English"
    mode: str = "patient"


class TranslateRequest(BaseModel):
    text: str
    target_language: str = "English"


class HealthResponse(BaseModel):
    status: str
    service: str
    llm: str
    provider: str
    message: str | None = None


def _error_payload(code: str, message: str, details: str | None = None) -> dict[str, Any]:
    payload = {"success": False, "error": code, "message": message}
    if details:
        payload["details"] = details
    return payload


def _raise_structured_error(code: str, message: str, details: str | None = None, status_code: int = 400):
    raise HTTPException(
        status_code=status_code,
        detail=_error_payload(code, message, details),
    )


def _clean_answer(answer: str) -> str:
    if not answer:
        return answer
    cleaned = answer.strip()
    for prefix in ("Answer:", "answer:", "Response:", "response:"):
        if cleaned.lower().startswith(prefix.lower()):
            cleaned = cleaned[len(prefix):].strip()
    return cleaned


def _generate_document_id(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def _extract_patient_metadata(text: str, filename: str) -> dict[str, Any]:
    metadata: dict[str, Any] = {"patient_name": None, "age": None, "sex": None, "doctor": None, "report_date": None}
    if not text:
        return metadata

    patient_match = re.search(r"(?i)patient\s*(?:name)?\s*[:=]?\s*([A-Z][A-Za-z .'-]+)", text)
    if patient_match:
        metadata["patient_name"] = patient_match.group(1).strip()

    age_match = re.search(r"(?i)\b(?:age|years?)\s*[:=]?\s*(\d{1,3})\b", text)
    if age_match:
        metadata["age"] = int(age_match.group(1))

    sex_match = re.search(r"(?i)\b(?:sex|gender)\s*[:=]?\s*(male|female|m|f)\b", text)
    if sex_match:
        metadata["sex"] = sex_match.group(1).strip().lower()

    doctor_match = re.search(r"(?i)(?:doctor|referred by|ref by|consultant)\s*[:=]?\s*([A-Za-z .'-]+)", text)
    if doctor_match:
        metadata["doctor"] = doctor_match.group(1).strip()

    date_match = re.search(r"(?i)(?:report date|date|issued on)\s*[:=]?\s*(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{2}-\d{2}-\d{4})", text)
    if date_match:
        metadata["report_date"] = date_match.group(1).strip()

    metadata["source_filename"] = filename
    return metadata


def _extract_text_from_report(file_path: str, extension: str) -> str:
    if extension == ".pdf":
        extracted = read_pdf(file_path)
        if extracted and extracted.strip():
            return extracted
        return extract_text_from_scanned_pdf(file_path)
    return extract_text_from_image(file_path)


def _store_chunks_for_document(document_id: str, filename: str, text: str) -> int:
    chunks = chunk_text(text)
    if not chunks:
        raise ValueError("No useful text sections were created from the report.")
    embeddings = create_embeddings(chunks)
    if embeddings is None or len(embeddings) == 0:
        raise ValueError("Embeddings could not be created.")
    stored = store_chunks(chunks, embeddings, document_id=document_id, filename=filename)
    return int(stored or len(chunks))


def _build_report_summary(report_id: str | None):
    if not report_id:
        return {"report_count": 0, "latest_report": None, "markers": [], "alerts": []}
    report = get_report(report_id)
    if not report:
        return {"report_count": 0, "latest_report": None, "markers": [], "alerts": []}
    return {
        "report_count": 1,
        "latest_report": report,
        "markers": [],
        "alerts": [],
    }


def _first_or_none(value):
    if isinstance(value, list):
        return value[0] if value else None
    return value


@app.get("/health")
def health_check() -> dict[str, Any]:
    provider = get_llm_provider()
    provider_name = type(provider).__name__.replace("LLMProvider", "").lower() if provider else "local"
    return {
        "status": "healthy",
        "service": "MediMind AI",
        "llm": os.getenv("OLLAMA_MODEL", "gemma3:4b"),
        "provider": provider_name,
        "message": "The app is available and the backend is responding.",
    }


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Welcome to MediMind AI", "docs": "/docs", "health": "/health"}


@app.get("/reports")
def list_report_metadata() -> dict[str, Any]:
    reports = list_reports()
    return {"success": True, "count": len(reports), "reports": reports}


@app.get("/reports/{report_id}")
def fetch_report(report_id: str) -> dict[str, Any]:
    report = get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    return {"success": True, "report": report}


@app.get("/patients/{patient_id}/reports")
def fetch_patient_reports(patient_id: str) -> dict[str, Any]:
    reports = get_patient_reports(patient_id)
    return {"success": True, "patient_id": patient_id, "reports": reports}


@app.get("/patients/{patient_id}/history")
def fetch_patient_history(patient_id: str) -> dict[str, Any]:
    history = get_patient_history(patient_id)
    return {"success": True, "patient_id": patient_id, **history}


@app.get("/patients/{patient_id}/dashboard")
def fetch_patient_dashboard(patient_id: str) -> dict[str, Any]:
    history = get_patient_history(patient_id)
    reports = history.get("reports", [])
    biomarkers = history.get("biomarkers", [])
    latest = reports[0] if reports else None
    return {
        "success": True,
        "patient_id": patient_id,
        "report_count": len(reports),
        "latest_report": latest,
        "biomarkers": biomarkers,
        "alerts": [entry for entry in biomarkers if entry.get("status") in {"high", "low", "critical"}],
    }


@app.get("/patients/{patient_id}")
def fetch_patient_profile(patient_id: str) -> dict[str, Any]:
    history = get_patient_history(patient_id)
    reports = history.get("reports", [])
    return {"success": True, "patient_id": patient_id, "report_count": len(reports), "history": history}


@app.get("/patients/{patient_id}/trends")
def fetch_patient_trends(patient_id: str) -> dict[str, Any]:
    history = get_patient_history(patient_id)
    markers = {}
    for row in history.get("biomarkers", []):
        markers.setdefault(row["biomarker_name"], []).append(row)
    return {"success": True, "patient_id": patient_id, "trends": markers}


@app.get("/patients/{patient_id}/insights")
def fetch_patient_insights(patient_id: str) -> dict[str, Any]:
    history = get_patient_history(patient_id)
    reports = history.get("reports", [])
    biomarkers = history.get("biomarkers", [])
    latest = reports[0] if reports else None
    insights = []
    if latest:
        insights.append({"type": "latest_report", "message": f"Latest report uploaded on {latest.get('report_date') or latest.get('upload_date')}.", "source": "structured_history"})
    if biomarkers:
        insights.append({"type": "marker_summary", "message": f"{len(biomarkers)} biomarker readings are currently available for this patient.", "source": "structured_history"})
    if not insights:
        insights.append({"type": "empty_state", "message": "No historical data is available yet. Upload a report to start monitoring trends.", "source": "structured_history"})
    return {"success": True, "patient_id": patient_id, "insights": insights}


@app.get("/patients/{patient_id}/risks")
def fetch_patient_risks(patient_id: str) -> dict[str, Any]:
    history = get_patient_history(patient_id)
    alerts = [entry for entry in history.get("biomarkers", []) if entry.get("status") in {"high", "low", "critical"}]
    return {"success": True, "patient_id": patient_id, "risks": alerts}


@app.post("/reports/upload")
@app.post("/upload")
@app.post("/documents/upload")
async def upload_report(file: UploadFile = File(...)) -> dict[str, Any]:
    if not file.filename:
        raise HTTPException(status_code=400, detail=_error_payload("INVALID_UPLOAD", "No filename provided."))

    extension = Path(file.filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=_error_payload("UNSUPPORTED_FILE_TYPE", "Only PDF, JPG, JPEG and PNG files are supported."))

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail=_error_payload("EMPTY_FILE", "Uploaded file is empty."))

    safe_filename = Path(file.filename).name
    save_path = REPORT_DIR / safe_filename
    save_path.write_bytes(file_bytes)

    try:
        extracted_text = _extract_text_from_report(str(save_path), extension)
    except Exception as exc:  # pragma: no cover - error path
        return JSONResponse(
            status_code=422,
            content=_error_payload(
                "REPORT_PROCESSING_FAILED",
                "The report could not be processed.",
                "No readable text was detected or the PDF could not be parsed.",
            ),
        )

    if not extracted_text or not extracted_text.strip():
        return JSONResponse(
            status_code=422,
            content=_error_payload(
                "REPORT_PROCESSING_FAILED",
                "The report could not be processed.",
                "No readable text was detected.",
            ),
        )

    metadata = _extract_patient_metadata(extracted_text, safe_filename)
    document_id = _generate_document_id(file_bytes)
    store_payload = persist_report(file_bytes, safe_filename, extracted_text, metadata)
    if store_payload.get("document_already_exists"):
        if document_id:
            try:
                _store_chunks_for_document(document_id, safe_filename, extracted_text)
            except Exception:
                pass
        return {"success": True, "message": "A matching report was already stored. Duplicate upload prevented.", "document_id": store_payload["report_id"], "patient_id": store_payload.get("patient_id"), "duplicate": True, "filename": safe_filename}

    try:
        chunks_stored = _store_chunks_for_document(document_id, safe_filename, extracted_text)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error while storing report: {str(exc)}") from exc

    return {
        "success": True,
        "message": "Your report has been analyzed.",
        "document_id": document_id,
        "report_id": store_payload.get("report_id"),
        "patient_id": store_payload.get("patient_id"),
        "filename": safe_filename,
        "chunks_stored": chunks_stored,
        "biomarkers_analyzed": store_payload.get("biomarkers", 0),
    }


@app.post("/chat")
@app.post("/documents/chat")
async def chat(request: ChatRequest) -> dict[str, Any]:
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    question_type = route_question(question)
    if question_type == "GENERAL":
        answer = generate_answer("", question, question_type="GENERAL")
        return {"success": True, "answer": _clean_answer(answer), "question_type": question_type, "sources": []}

    if not request.document_id:
        return {
            "success": True,
            "answer": "Please upload your medical report first so I can check this result against the report.",
            "question_type": question_type,
            "sources": [],
        }

    try:
        results = retrieve_chunks(question, top_k=3, document_id=request.document_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error while searching the report: {str(exc)}") from exc

    docs = []
    if isinstance(results, dict):
        raw_documents = results.get("documents", [])
        if raw_documents:
            docs = raw_documents[0] if isinstance(raw_documents[0], list) else raw_documents
    if not docs:
        return {"success": True, "answer": "I could not find that information in the uploaded report.", "question_type": question_type, "sources": []}

    context = build_context(docs)
    answer = generate_answer(context, question, question_type=question_type)
    return {
        "success": True,
        "answer": _clean_answer(answer),
        "question_type": question_type,
        "sources": _first_or_none(results.get("metadatas", [])) if isinstance(results, dict) else [],
    }


@app.post("/chat/translate")
async def translate_chat(request: TranslateRequest) -> dict[str, Any]:
    provider = get_llm_provider()
    translated = provider.translate(request.text, request.target_language)
    return {"success": True, "translated_text": translated, "target_language": request.target_language}


@app.post("/voice/transcribe")
async def voice_transcribe() -> dict[str, Any]:
    return {"success": True, "message": "Voice transcription is enabled through browser microphone access when available.", "provider": "browser"}


@app.post("/voice/speak")
async def voice_speak() -> dict[str, Any]:
    return {"success": True, "message": "Text-to-speech is available in the browser when enabled.", "provider": "browser"}


@app.get("/health-check")
def health_check_alias() -> dict[str, Any]:
    return health_check()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8080, reload=False)
