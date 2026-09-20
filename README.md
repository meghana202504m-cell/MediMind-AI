# MediMind AI

MediMind AI is a healthcare report assistant designed to analyze uploaded medical reports, answer general and report-specific questions, and maintain a lightweight longitudinal health history for trend monitoring.

## Overview

This project combines:

- FastAPI backend with secure upload and chat endpoints
- React + Vite frontend
- ChromaDB vector retrieval for report chunks
- OCR and PDF/image processing for lab reports and scans
- SQLite-based structured storage for patient history and biomarker records
- Local LLM support via Ollama with graceful fallback when unavailable

## Architecture

- Backend API: app.py
- Structured storage: backend/structured_store.py
- LLM abstraction: backend/llm_provider.py
- RAG utilities: rag/
- Frontend UI: frontend/

## Features

- Medical PDF and image upload
- OCR fallback for scanned PDFs
- Word-level and document-level report retrieval
- Chat for general, report-specific, and mixed medical questions
- Duplicate report protection via content hash
- Basic patient history and dashboard endpoints
- Local AI provider abstraction with cloud option for future expansion
- Privacy-first configuration through environment variables

## Tech stack

- Python 3.11
- FastAPI
- SQLite
- ChromaDB
- SentenceTransformers
- EasyOCR / PyMuPDF / pypdf
- React + Vite
- Ollama

## Setup

1. Create a virtual environment and install dependencies.
2. Copy .env.example to .env and adjust values as needed.
3. Start Ollama if using the local model.
4. Run the FastAPI backend and frontend separately.

## Environment variables

Sample values are in [.env.example](.env.example).

- AI_PROVIDER=local
- OLLAMA_URL=http://127.0.0.1:11434/api/generate
- OLLAMA_MODEL=gemma3:4b
- OPENAI_API_KEY=
- CORS_ORIGINS=http://localhost:3000,http://localhost:5173

## Running backend

```bash
python -m uvicorn app:app --host 0.0.0.0 --port 8080 --reload
```

## Running frontend

```bash
cd frontend
npm install
npm run dev
```

## API notes

- /health checks backend availability
- /upload or /reports/upload handles PDF/image uploads
- /chat answers questions using report context when available
- /reports and /patients/{patient_id}/history provide structured history data
- /chat/translate and the browser voice routes are available as interface hooks

## Privacy and safety

- Do not commit real API keys.
- Keep sensitive medical data local by default.
- The app should not expose internal stack traces to end users.
- Local AI is preferred; cloud AI is optional and should be configured only when needed.
- All medical answers are educational and not a substitute for professional care.

## Testing

```bash
python -m pytest -q
```
