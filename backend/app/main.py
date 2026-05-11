from __future__ import annotations

from app.runtime_bootstrap import enforce_known_good_runtime

enforce_known_good_runtime()

import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import Settings, get_settings
from app.models.schemas import ChatRequest, ChatResponse
from app.rag.preprocess import ensure_processed_catalog, ensure_raw_catalog_present
from app.rag.vector_store import FaissRetriever
from app.services.chat_agent import ChatOrchestrator
from app.services.groq_client import GroqClient
from app.utils.logging_config import setup_logging


def backend_dir() -> Path:
    # backend/app/main.py -> backend/
    return Path(__file__).resolve().parents[1]


load_dotenv(dotenv_path=backend_dir() / ".env", override=False)

log = logging.getLogger(__name__)

_orchestrator: ChatOrchestrator | None = None


def data_dir(settings: Settings) -> Path:
    if settings.backend_data_dir:
        return Path(settings.backend_data_dir)
    return backend_dir() / "data"


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(level=get_settings().log_level)

    settings = get_settings()

    bd = backend_dir()
    dd = data_dir(settings)
    raw_path = dd / "shl_catalog.json"
    processed_path = dd / "processed_catalog.json"
    idx_dir = dd / "faiss_store"

    try:
        await ensure_raw_catalog_present(settings, raw_path)
        processed = ensure_processed_catalog(raw_path=raw_path, processed_path=processed_path)
        retriever = FaissRetriever(
            assessments=processed,
            embedding_model_name=settings.embedding_model,
            index_dir=idx_dir,
        )
        groq: GroqClient | None = None
        try:
            if settings.groq_api_key.strip():
                groq = GroqClient(settings)
            else:
                log.warning("GROQ_API_KEY missing: /chat operates in degraded retrieval-only fallback.")
        except Exception as exc:  # noqa: BLE001
            log.exception("Failed to initialize Groq client err=%s", exc)
            groq = None

        global _orchestrator  # noqa: PLW0603
        _orchestrator = ChatOrchestrator(
            settings=settings,
            retriever=retriever,
            groq=groq,
        )
    except Exception as exc:
        log.exception("Startup failed catastrophically err=%s", exc)
        raise

    yield


app = FastAPI(
    title="Conversational SHL Assessment Recommender",
    version="1.0.0",
    lifespan=lifespan,
)

settings_singleton = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings_singleton.cors_origins_list(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    try:
        response = await call_next(request)
        return response
    finally:
        ms = int((time.perf_counter() - start) * 1000)
        log.info("%s %s %sms", request.method, request.url.path, ms)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
async def root() -> dict[str, str]:
    return {"status": "ok", "message": "Backend is alive"}


@app.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    orch = globals().get("_orchestrator", None)

    if orch is None:
        raise HTTPException(status_code=503, detail="Service not initialized.")

    return await orch.reply(payload.messages)


__all__ = ["app"]
