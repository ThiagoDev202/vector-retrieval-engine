"""DTOs de entrada e saída para o módulo de busca semântica."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

_ALLOWED_METADATA_VALUE_TYPES = (str, int, float, bool, type(None))
_MAX_METADATA_KEYS = 20
_MAX_METADATA_VALUE_LEN = 2_000


class DocumentIn(BaseModel):
    """Payload de criação de documento."""

    model_config = ConfigDict(extra="forbid")

    id: str | None = Field(default=None, min_length=1, max_length=128)
    content: str = Field(..., min_length=1, max_length=50_000)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata")
    @classmethod
    def _validate_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        """Valida limites e tipos dos valores do metadata."""
        if len(value) > _MAX_METADATA_KEYS:
            raise ValueError(f"metadata excede {_MAX_METADATA_KEYS} chaves")
        for val in value.values():
            if not isinstance(val, _ALLOWED_METADATA_VALUE_TYPES):
                raise ValueError(
                    "metadata aceita apenas valores primitivos (str, int, float, bool, None)"
                )
            if isinstance(val, str) and len(val) > _MAX_METADATA_VALUE_LEN:
                raise ValueError(f"valor de metadata excede {_MAX_METADATA_VALUE_LEN} caracteres")
        return value


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

    query: str = Field(..., min_length=1, max_length=2_000)
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
