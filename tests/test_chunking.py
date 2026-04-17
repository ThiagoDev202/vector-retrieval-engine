"""Testes unitários para split_text."""

import pytest

from app.search.chunking import split_text
from app.search.embedder import FakeEmbedder


def test_short_text_returns_single_chunk() -> None:
    """Texto menor que chunk_size retorna o próprio texto como chunk único."""
    embedder = FakeEmbedder()
    text = "um dois tres"
    chunks = split_text(
        text,
        chunk_size=10,
        overlap=2,
        tokenize=embedder.tokenize,
        detokenize=embedder.detokenize,
    )
    assert chunks == [text]


def test_long_text_produces_overlapping_chunks() -> None:
    """Texto longo é dividido em chunks com sobreposição esperada."""
    embedder = FakeEmbedder()
    words = [f"w{i}" for i in range(12)]
    text = " ".join(words)

    chunks = split_text(
        text,
        chunk_size=5,
        overlap=2,
        tokenize=embedder.tokenize,
        detokenize=embedder.detokenize,
    )

    # step = 3, tokens = 12 → starts em 0, 3, 6, 9 → 4 chunks
    assert len(chunks) == 4
    assert chunks[0] == "w0 w1 w2 w3 w4"
    assert chunks[1] == "w3 w4 w5 w6 w7"
    assert chunks[2] == "w6 w7 w8 w9 w10"
    assert chunks[3] == "w9 w10 w11"

    # sobreposição: últimas 2 palavras do chunk n == primeiras 2 do chunk n+1
    for i in range(len(chunks) - 1):
        tail = chunks[i].split()[-2:]
        head = chunks[i + 1].split()[:2]
        assert tail == head


def test_chunk_size_zero_raises_value_error() -> None:
    """chunk_size inválido dispara ValueError."""
    embedder = FakeEmbedder()
    with pytest.raises(ValueError, match="chunk_size"):
        split_text(
            "algum texto",
            chunk_size=0,
            overlap=0,
            tokenize=embedder.tokenize,
            detokenize=embedder.detokenize,
        )


def test_overlap_greater_or_equal_chunk_size_raises() -> None:
    """overlap >= chunk_size é proibido."""
    embedder = FakeEmbedder()
    with pytest.raises(ValueError, match="overlap"):
        split_text(
            "algum texto",
            chunk_size=3,
            overlap=3,
            tokenize=embedder.tokenize,
            detokenize=embedder.detokenize,
        )


def test_empty_text_returns_empty_list() -> None:
    """Texto vazio retorna lista vazia."""
    embedder = FakeEmbedder()
    assert (
        split_text(
            "",
            chunk_size=5,
            overlap=1,
            tokenize=embedder.tokenize,
            detokenize=embedder.detokenize,
        )
        == []
    )


def test_whitespace_only_text_returns_empty_list() -> None:
    """Texto só com whitespace retorna lista vazia."""
    embedder = FakeEmbedder()
    assert (
        split_text(
            "   \n\t  ",
            chunk_size=5,
            overlap=1,
            tokenize=embedder.tokenize,
            detokenize=embedder.detokenize,
        )
        == []
    )
