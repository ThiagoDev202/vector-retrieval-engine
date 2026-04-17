"""Testes para app/core/config.py."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_defaults() -> None:
    """Verifica que os valores padrão batem com os esperados."""
    s = Settings()
    assert s.app_env == "dev"
    assert s.embedding_model == "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    assert s.embedding_dim == 384
    assert s.chunk_size == 256
    assert s.chunk_overlap == 32
    assert s.default_top_k == 5
    assert s.bootstrap_on_startup is True


def test_chunk_overlap_gte_chunk_size_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Valida que chunk_overlap >= chunk_size dispara ValidationError."""
    monkeypatch.setenv("CHUNK_SIZE", "64")
    monkeypatch.setenv("CHUNK_OVERLAP", "64")

    with pytest.raises(ValidationError):
        Settings()


def test_chunk_size_env_var_respected(monkeypatch: pytest.MonkeyPatch) -> None:
    """Valida que CHUNK_SIZE via env var é aplicado corretamente."""
    monkeypatch.setenv("CHUNK_SIZE", "128")
    monkeypatch.setenv("CHUNK_OVERLAP", "16")

    s = Settings()
    assert s.chunk_size == 128
    assert s.chunk_overlap == 16
