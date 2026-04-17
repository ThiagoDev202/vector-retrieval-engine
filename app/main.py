"""Ponto de entrada da aplicação FastAPI."""

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.responses import Response

from app.core.config import get_settings
from app.core.exceptions import DocumentNotFoundError, EmbeddingError, IndexUnavailableError
from app.core.logging import configure_logging
from app.search.embedder import SentenceTransformerEmbedder
from app.search.ingestion import load_corpus
from app.search.router import router
from app.search.service import SearchService
from app.search.store import FaissVectorStore

configure_logging()


def register_exception_handlers(application: FastAPI) -> None:
    """Registra handlers centralizados para erros de domínio."""

    @application.exception_handler(DocumentNotFoundError)
    async def handle_document_not_found(
        request: Request, exc: DocumentNotFoundError
    ) -> JSONResponse:
        content: dict[str, Any] = {"detail": "documento não encontrado"}
        if get_settings().app_env != "prod":
            content["document_id"] = exc.document_id
        return JSONResponse(status_code=404, content=content)

    @application.exception_handler(IndexUnavailableError)
    async def handle_index_unavailable(
        request: Request, exc: IndexUnavailableError
    ) -> JSONResponse:
        content: dict[str, Any] = {"detail": "índice indisponível"}
        if get_settings().app_env != "prod":
            error_str = str(exc)
            if error_str:
                content["error"] = error_str
        return JSONResponse(status_code=503, content=content)

    @application.exception_handler(EmbeddingError)
    async def handle_embedding_error(request: Request, exc: EmbeddingError) -> JSONResponse:
        content: dict[str, Any] = {"detail": "falha ao gerar embedding"}
        if get_settings().app_env != "prod":
            error_str = str(exc)
            if error_str:
                content["error"] = error_str
        return JSONResponse(status_code=500, content=content)


def _register_body_size_limit(application: FastAPI, max_bytes: int = 1_048_576) -> None:
    """Rejeita requests com Content-Length acima do limite configurado."""

    @application.middleware("http")
    async def _enforce_body_size(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        content_length_raw = request.headers.get("content-length")
        if content_length_raw is not None:
            try:
                content_length = int(content_length_raw)
            except ValueError:
                content_length = 0
            if content_length > max_bytes:
                return JSONResponse(
                    status_code=413,
                    content={"detail": "payload excede o tamanho máximo de 1 MiB"},
                )
        return await call_next(request)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Inicializa embedder, store e SearchService no startup da aplicação."""
    settings = get_settings()
    embedder = SentenceTransformerEmbedder(settings.embedding_model)
    embedder.load()
    if embedder.dimension != settings.embedding_dim:
        raise IndexUnavailableError(
            f"dimensão do modelo ({embedder.dimension}) difere de"
            f" EMBEDDING_DIM ({settings.embedding_dim})"
        )
    store = FaissVectorStore(settings.index_dir, settings.embedding_dim)
    await store.load()
    service = SearchService(
        embedder=embedder,
        store=store,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        default_top_k=settings.default_top_k,
        embedding_model_name=settings.embedding_model,
    )
    application.state.search_service = service

    if settings.bootstrap_on_startup and int(store.stats()["chunk_count"]) == 0:
        await load_corpus(settings.corpus_dir, service)

    yield


def create_app(*, lifespan_override: Callable[..., Any] | None = None) -> FastAPI:
    """Cria e configura a instância FastAPI."""
    application = FastAPI(
        title="Vector Retrieval Engine",
        description="API REST de busca semântica com embeddings locais e FAISS.",
        version="0.1.0",
        docs_url="/docs",
        openapi_url="/api/v1/openapi.json",
        lifespan=lifespan_override or lifespan,
    )
    configure_logging()
    settings = get_settings()
    allow_origins = ["*"] if settings.app_env != "prod" else []
    application.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type", "Accept"],
        max_age=600,
    )
    _register_body_size_limit(application)
    register_exception_handlers(application)
    application.include_router(router)
    return application


app = create_app()
