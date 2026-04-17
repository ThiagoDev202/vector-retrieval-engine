"""Ponto de entrada da aplicação FastAPI."""

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.exceptions import DocumentNotFoundError, EmbeddingError, IndexUnavailableError
from app.core.logging import configure_logging
from app.search.embedder import SentenceTransformerEmbedder
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
        return JSONResponse(
            status_code=404,
            content={"detail": str(exc) or "documento não encontrado"},
        )

    @application.exception_handler(IndexUnavailableError)
    async def handle_index_unavailable(
        request: Request, exc: IndexUnavailableError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"detail": str(exc) or "índice indisponível"},
        )

    @application.exception_handler(EmbeddingError)
    async def handle_embedding_error(request: Request, exc: EmbeddingError) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc) or "falha ao gerar embedding"},
        )


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
    # TODO(fase 6): bootstrap_corpus se bootstrap_on_startup e índice vazio.
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
    register_exception_handlers(application)
    application.include_router(router)
    return application


app = create_app()
