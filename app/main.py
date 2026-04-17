"""Ponto de entrada da aplicação FastAPI."""

from fastapi import APIRouter, FastAPI

app = FastAPI(
    title="Vector Retrieval Engine",
    description="API REST de busca semântica com embeddings locais e FAISS.",
    version="0.1.0",
    docs_url="/docs",
    openapi_url="/api/v1/openapi.json",
)

api_router = APIRouter(prefix="/api/v1")


@api_router.get("/health")
async def health() -> dict[str, str | bool]:
    """Retorna liveness e readiness do serviço."""
    return {"status": "ok", "index_ready": False}


app.include_router(api_router)
