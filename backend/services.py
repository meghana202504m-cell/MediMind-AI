import logging
import os
import re
import tempfile
from pathlib import Path

from rag.chunker import chunk_text
from rag.context_builder import build_context
from rag.embedder import create_embeddings
from rag.image_reader import extract_text_from_image, extract_text_from_scanned_pdf
from rag.llm import generate_answer
from rag.pdf_reader import read_pdf
from rag.question_router import route_question
from rag.report_parser import structure_report
from rag.retriever import retrieve_chunks
from rag.text_cleaner import clean_ocr_text
from rag.vector_store import collection, document_id_from_file, store_chunks


logger = logging.getLogger(__name__)
SUPPORTED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
SESSION_MEMORY = {}


def _session_key(document_id):
    return document_id or "default"


def _recent_conversation(question, document_id=None):
    normalized = re.sub(r"\s+", " ", (question or "").strip().lower())
    if not re.search(r"\b(that|this|it|they|those|result|value|level)\b", normalized):
        return ""

    history = SESSION_MEMORY.get(_session_key(document_id), [])
    if not history:
        return ""

    previous = history[-1]
    return (
        "Relevant prior context: The user previously asked, '"
        f"{previous['question']}'. The answer was: {previous['answer']}"
    )


def _remember_conversation(question, answer, document_id=None):
    key = _session_key(document_id)
    history = SESSION_MEMORY.setdefault(key, [])
    history.append({"question": question, "answer": answer})
    if len(history) > 5:
        history = history[-5:]
    SESSION_MEMORY[key] = history


def process_uploaded_document(filename, content):
    extension = Path(filename or "").suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError("Unsupported file type. Use PDF, JPG, JPEG, or PNG.")

    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            suffix=extension,
            delete=False
        ) as temporary_file:
            temporary_file.write(content)
            temporary_path = temporary_file.name

        if extension == ".pdf":
            extracted_text = read_pdf(temporary_path)
            if not extracted_text.strip():
                extracted_text = extract_text_from_scanned_pdf(temporary_path)
        else:
            extracted_text = extract_text_from_image(temporary_path)

        if not extracted_text.strip():
            raise ValueError("No text could be extracted from the document.")

        cleaned_text = clean_ocr_text(extracted_text)
        structured_text = structure_report(cleaned_text)
        chunks = chunk_text(structured_text)
        if not chunks:
            raise ValueError("No report chunks were created.")

        embeddings = create_embeddings(chunks)
        document_id = document_id_from_file(temporary_path)
        store_chunks(
            chunks,
            embeddings,
            document_id=document_id,
            filename=Path(filename).name
        )

        return {
            "success": True,
            "document_id": document_id,
            "filename": Path(filename).name,
            "chunks": len(chunks),
            "message": "Document processed successfully"
        }
    except Exception:
        logger.exception("Document processing failed for %s", filename)
        raise
    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.remove(temporary_path)


def answer_question(question, document_id=None):
    question_type = route_question(question)
    recent_context = _recent_conversation(question, document_id)
    combined_question = question
    if recent_context:
        combined_question = (
            f"{question} IMPORTANT CONTEXT: {recent_context}"
        )

    if question_type == "GENERAL":
        answer = generate_answer("", combined_question, question_type="GENERAL")
        _remember_conversation(question, answer, document_id)
        return {
            "answer": answer,
            "question_type": question_type,
            "sources": []
        }

    if not document_id:
        answer = (
            "Please upload your medical report first so I can check this result "
            "against the report."
        )
        _remember_conversation(question, answer, document_id)
        return {
            "answer": answer,
            "question_type": question_type,
            "sources": []
        }

    results = retrieve_chunks(question, top_k=3, document_id=document_id)
    documents = results.get("documents", [[]])[0]
    if not documents:
        answer = "I could not find that information in the uploaded report."
        _remember_conversation(question, answer, document_id)
        return {
            "answer": answer,
            "question_type": question_type,
            "sources": []
        }

    context = build_context(documents)
    answer = generate_answer(context, combined_question, question_type=question_type)
    _remember_conversation(question, answer, document_id)
    return {
        "answer": answer,
        "question_type": question_type,
        "sources": []
    }
