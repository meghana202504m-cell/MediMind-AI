import logging
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.services import answer_question, process_uploaded_document


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="MediMind AI API",
    version="1.0.0",
    description="API access to the MediMind medical-document RAG pipeline."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"]
)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)
    document_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
    question_type: str
    sources: list[dict[str, Any]] = []


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "MediMind AI"}


@app.post("/upload")
@app.post("/documents/upload")
def upload_document(file: UploadFile | None = File(default=None)) -> dict[str, Any]:
    if file is None or not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded.")

    try:
        content = file.file.read()
        if not content:
            raise ValueError("The uploaded file is empty.")
        result = process_uploaded_document(file.filename, content)
        return {
            "success": True,
            "document_id": result["document_id"],
            "filename": result["filename"],
            "message": result.get(
                "message",
                "Document processed successfully."
            )
        }
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        logger.exception("Upload endpoint failed for %s", file.filename)
        raise HTTPException(
            status_code=500,
            detail="Document processing failed."
        ) from error


@app.post("/chat")
@app.post("/documents/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        result = answer_question(question, document_id=request.document_id)
        return ChatResponse(
            answer=result["answer"],
            question_type=result.get("question_type", "REPORT"),
            sources=result.get("sources", [])
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except Exception as error:
        logger.exception("Chat endpoint failed")
        raise HTTPException(
            status_code=503,
            detail="The answer service is currently unavailable."
        ) from error
