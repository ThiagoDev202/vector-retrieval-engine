"""Endpoints HTTP do módulo de busca semântica."""

from fastapi import APIRouter, Depends, Request, status

from app.core.exceptions import IndexUnavailableError
from app.search.schemas import (
    DocumentDetail,
    DocumentIn,
    DocumentOut,
    HealthResponse,
    SearchQuery,
    SearchResponse,
    StatsResponse,
)
from app.search.service import SearchService

router = APIRouter(prefix="/api/v1", tags=["search"])


def get_search_service(request: Request) -> SearchService:
    """Lê o singleton de app.state.search_service (criado no lifespan)."""
    service: SearchService | None = getattr(request.app.state, "search_service", None)
    if service is None:
        raise IndexUnavailableError("serviço de busca não inicializado")
    return service


@router.get("/health", response_model=HealthResponse)
async def health_endpoint(
    service: SearchService = Depends(get_search_service),  # noqa: B008
) -> HealthResponse:
    """Retorna liveness e readiness do serviço de busca."""
    return service.health()


@router.get("/stats", response_model=StatsResponse)
async def stats_endpoint(
    service: SearchService = Depends(get_search_service),  # noqa: B008
) -> StatsResponse:
    """Retorna estatísticas agregadas do índice vetorial."""
    return service.stats()


@router.post("/search", response_model=SearchResponse)
async def search_endpoint(
    query: SearchQuery,
    service: SearchService = Depends(get_search_service),  # noqa: B008
) -> SearchResponse:
    """Executa busca semântica e retorna os hits mais relevantes."""
    return await service.search(query)


@router.post("/documents", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def create_document(
    payload: DocumentIn,
    service: SearchService = Depends(get_search_service),  # noqa: B008
) -> DocumentOut:
    """Indexa um novo documento particionando em chunks com embeddings."""
    return await service.add_document(payload)


@router.get("/documents/{document_id}", response_model=DocumentDetail)
async def read_document(
    document_id: str,
    service: SearchService = Depends(get_search_service),  # noqa: B008
) -> DocumentDetail:
    """Retorna todos os chunks de um documento pelo seu ID."""
    return await service.get_document(document_id)


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document_endpoint(
    document_id: str,
    service: SearchService = Depends(get_search_service),  # noqa: B008
) -> None:
    """Remove um documento e todos os seus chunks do índice."""
    await service.delete_document(document_id)
