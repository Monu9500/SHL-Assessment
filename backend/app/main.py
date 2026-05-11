from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import Settings, get_settings
from app.models.schemas import ChatRequest, ChatResponse
from app.rag.preprocess import (
    ensure_processed_catalog,
    ensure_raw_catalog_present,
)
from app.services.chat_agent import ChatOrchestrator
from app.services.groq_client import GroqClient
from app.utils.logging_config import setup_logging


def backend_dir() -> Path:
    return Path(__file__).resolve().parents[1]


# Load environment variables
load_dotenv(dotenv_path=backend_dir() / ".env", override=False)

log = logging.getLogger(__name__)

# Global orchestrator
_orchestrator: ChatOrchestrator | None = None


def data_dir(settings: Settings) -> Path:
    if settings.backend_data_dir:
        return Path(settings.backend_data_dir)

    return backend_dir() / "data"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup lifecycle.
    """

    setup_logging(level=get_settings().log_level)

    settings = get_settings()

    dd = data_dir(settings)

    raw_path = dd / "shl_catalog.json"
    processed_path = dd / "processed_catalog.json"

    try:
        log.info("Starting backend initialization...")

        # Download SHL catalog if missing
        await ensure_raw_catalog_present(settings, raw_path)

        # Build processed catalog
        processed = ensure_processed_catalog(
            raw_path=raw_path,
            processed_path=processed_path,
        )

        log.info(
            "Catalog preprocessing complete. assessments=%s",
            len(processed),
        )

        # Initialize Groq client
        groq: GroqClient | None = None

        try:
            if settings.groq_api_key.strip():
                groq = GroqClient(settings)
                log.info("Groq client initialized.")

            else:
                log.warning(
                    "GROQ_API_KEY missing. Running in fallback mode."
                )

        except Exception as exc:
            log.exception(
                "Failed to initialize Groq client: %s",
                exc,
            )

            groq = None

        # IMPORTANT:
        # Using lightweight retrieval (no FAISS / transformers)
        _retriever = processed

        global _orchestrator

        _orchestrator = ChatOrchestrator(
            settings=settings,
            retriever=_retriever,
            groq=groq,
        )

        log.info("Chat orchestrator initialized successfully.")

    except Exception as exc:
        log.exception("Startup failed: %s", exc)
        raise

    yield

    log.info("Application shutdown complete.")


# FastAPI app
app = FastAPI(
    title="Conversational SHL Assessment Recommender",
    version="1.0.0",
    lifespan=lifespan,
)

# Settings
settings_singleton = get_settings()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings_singleton.cors_origins_list(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# Logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()

    try:
        response = await call_next(request)
        return response

    finally:
        ms = int((time.perf_counter() - start) * 1000)

        log.info(
            "%s %s %sms",
            request.method,
            request.url.path,
            ms,
        )


# Health endpoint
@app.get("/health")
async def health():
    return {"status": "ok"}


# Root endpoint
@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "Conversational SHL Assessment Recommender API is running",
    }


# Chat endpoint
@app.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest):

    orch = _orchestrator

    if orch is None:
        raise HTTPException(
            status_code=503,
            detail="Service not initialized.",
        )

    return await orch.reply(payload.messages)


__all__ = ["app"]