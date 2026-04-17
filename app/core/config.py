"""Configurações da aplicação via variáveis de ambiente."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações carregadas do ambiente ou arquivo .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["dev", "test", "prod"] = "dev"

    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_dim: int = Field(default=384, gt=0)

    index_dir: Path = Path("./data/index")
    corpus_dir: Path = Path("./data/raw")

    chunk_size: int = Field(default=256, gt=0)
    chunk_overlap: int = Field(default=32, ge=0)

    default_top_k: int = Field(default=5, gt=0)
    bootstrap_on_startup: bool = True

    @model_validator(mode="after")
    def validate_chunk_overlap(self) -> "Settings":
        """Garante que chunk_overlap seja menor que chunk_size."""
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError(
                f"chunk_overlap ({self.chunk_overlap}) deve ser menor que"
                f" chunk_size ({self.chunk_size})"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """Retorna instância cacheada de Settings para injeção via Depends."""
    return Settings()
