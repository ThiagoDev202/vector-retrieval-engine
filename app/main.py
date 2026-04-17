"""Ponto de entrada da aplicação FastAPI."""

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import DocumentNotFoundError, EmbeddingError, IndexUnavailableError
from app.core.logging import configure_logging

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


app = FastAPI(
    title="Vector Retrieval Engine",
    description="API REST de busca semântica com embeddings locais e FAISS.",
    version="0.1.0",
    docs_url="/docs",
    openapi_url="/api/v1/openapi.json",
)

register_exception_handlers(app)

api_router = APIRouter(prefix="/api/v1")


@api_router.get("/health")
async def health() -> dict[str, str | bool]:
    """Retorna liveness e readiness do serviço."""
    return {"status": "ok", "index_ready": False}


app.include_router(api_router)
