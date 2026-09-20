"""Canonical FastAPI application entry point.

The full API is implemented in the root application module. Re-exporting it
here keeps ``uvicorn backend.main:app`` as the supported launch command while
avoiding two divergent API implementations.
"""

from app import app

__all__ = ["app"]
