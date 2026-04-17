"""DTOs de entrada e saída para o módulo de busca semântica."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DocumentIn(BaseModel):
    """Payload de criação de documento."""

    model_config = ConfigDict(extra="forbid")

    id: str | None = Field(default=None, min_length=1, max_length=128)
    content: str = Field(..., min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentOut(BaseModel):
    """Resposta após indexar um documento."""

    document_id: str
    chunk_count: int
    dimension: int


class ChunkOut(BaseModel):
    """Representação de um chunk de documento."""

    chunk_idx: int
    text: str
    metadata: dict[str, Any]


class DocumentDetail(BaseModel):
    """Detalhes de um documento com todos os seus chunks."""

    document_id: str
    chunks: list[ChunkOut]
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchQuery(BaseModel):
    """Parâmetros de uma consulta de busca semântica."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=1)
    top_k: int | None = Field(default=None, gt=0, le=50)


class SearchHitOut(BaseModel):
    """Um resultado individual de busca semântica."""

    document_id: str
    chunk: str
    chunk_idx: int
    score: float
    metadata: dict[str, Any]


class SearchResponse(BaseModel):
    """Resposta completa de uma busca semântica."""

    query: str
    hits: list[SearchHitOut]


class StatsResponse(BaseModel):
    """Estatísticas agregadas do índice vetorial."""

    document_count: int
    chunk_count: int
    embedding_model: str
    dimension: int


class HealthResponse(BaseModel):
    """Status de saúde do serviço de busca."""

    status: str
    index_ready: bool
