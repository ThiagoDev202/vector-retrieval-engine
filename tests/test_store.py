"""Testes unitários para FaissVectorStore."""

from pathlib import Path

import numpy as np
import pytest
from numpy.typing import NDArray

from app.core.exceptions import DocumentNotFoundError, IndexUnavailableError
from app.search.store import ChunkRecord, FaissVectorStore, SearchHit

DIM = 384


def _random_normalized(n: int, dim: int = DIM, seed: int = 42) -> NDArray[np.float32]:
    """Gera ``n`` vetores aleatórios L2-normalizados em float32."""
    rng = np.random.default_rng(seed)
    raw = rng.standard_normal((n, dim)).astype(np.float32)
    norms = np.linalg.norm(raw, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (raw / norms).astype(np.float32)


async def test_add_and_search(tmp_path: Path) -> None:
    """Busca com vetor igual ao 1º chunk retorna esse chunk no topo com score ~1.0."""
    store = FaissVectorStore(tmp_path, DIM)
    chunks = ["chunk zero", "chunk um", "chunk dois"]
    vectors = _random_normalized(3)

    inserted = await store.add("doc-1", chunks, vectors, metadata={"title": "A"})
    assert inserted == 3

    hits = await store.search(vectors[0], top_k=3)
    assert len(hits) == 3
    assert isinstance(hits[0], SearchHit)
    assert hits[0].document_id == "doc-1"
    assert hits[0].chunk == "chunk zero"
    assert hits[0].chunk_idx == 0
    assert hits[0].score == pytest.approx(1.0, abs=1e-4)
    assert hits[0].metadata == {"title": "A"}


async def test_add_duplicate_document_raises(tmp_path: Path) -> None:
    """Reinserir o mesmo ``document_id`` levanta ValueError."""
    store = FaissVectorStore(tmp_path, DIM)
    vectors = _random_normalized(1)
    await store.add("doc-1", ["a"], vectors)

    with pytest.raises(ValueError, match="já indexado"):
        await store.add("doc-1", ["a"], vectors)


async def test_add_shape_mismatch_raises(tmp_path: Path) -> None:
    """Shape ou dtype incompatível levanta ValueError."""
    store = FaissVectorStore(tmp_path, DIM)

    wrong_shape = np.zeros((2, DIM), dtype=np.float32)
    with pytest.raises(ValueError):
        await store.add("doc-1", ["a"], wrong_shape)

    wrong_dim = np.zeros((1, DIM - 1), dtype=np.float32)
    with pytest.raises(ValueError):
        await store.add("doc-2", ["a"], wrong_dim)

    wrong_dtype = np.zeros((1, DIM), dtype=np.float64)
    with pytest.raises(ValueError):
        await store.add("doc-3", ["a"], wrong_dtype)  # type: ignore[arg-type]


async def test_add_empty_noop(tmp_path: Path) -> None:
    """Adicionar lista vazia retorna 0 e não altera o estado."""
    store = FaissVectorStore(tmp_path, DIM)
    empty = np.zeros((0, DIM), dtype=np.float32)

    inserted = await store.add("doc-empty", [], empty)
    assert inserted == 0
    assert store.stats()["chunk_count"] == 0
    assert store.stats()["document_count"] == 0


async def test_search_top_k_clamped(tmp_path: Path) -> None:
    """``top_k`` maior que ``ntotal`` é limitado ao tamanho do índice."""
    store = FaissVectorStore(tmp_path, DIM)
    vectors = _random_normalized(2)
    await store.add("doc-1", ["a", "b"], vectors)

    hits = await store.search(vectors[0], top_k=5)
    assert len(hits) == 2
    for hit in hits:
        assert hit.document_id == "doc-1"


async def test_search_empty_index(tmp_path: Path) -> None:
    """Buscar em índice vazio retorna lista vazia."""
    store = FaissVectorStore(tmp_path, DIM)
    query = _random_normalized(1)[0]
    assert await store.search(query, top_k=5) == []


async def test_search_invalid_top_k(tmp_path: Path) -> None:
    """``top_k <= 0`` levanta ValueError."""
    store = FaissVectorStore(tmp_path, DIM)
    query = _random_normalized(1)[0]

    with pytest.raises(ValueError):
        await store.search(query, top_k=0)
    with pytest.raises(ValueError):
        await store.search(query, top_k=-3)


async def test_get_document(tmp_path: Path) -> None:
    """``get_document`` retorna chunks ordenados por ``chunk_idx``."""
    store = FaissVectorStore(tmp_path, DIM)
    chunks = ["c0", "c1", "c2"]
    vectors = _random_normalized(3)
    await store.add("doc-1", chunks, vectors, metadata={"title": "X"})

    records = await store.get_document("doc-1")
    assert [r.chunk_idx for r in records] == [0, 1, 2]
    assert [r.chunk_text for r in records] == chunks
    assert all(isinstance(r, ChunkRecord) for r in records)
    assert records[0].metadata == {"title": "X"}


async def test_get_document_not_found(tmp_path: Path) -> None:
    """``get_document`` em id inexistente levanta DocumentNotFoundError."""
    store = FaissVectorStore(tmp_path, DIM)
    with pytest.raises(DocumentNotFoundError):
        await store.get_document("missing")


async def test_delete_removes_chunks(tmp_path: Path) -> None:
    """``delete`` remove todos os chunks do documento e reconstrói o índice."""
    store = FaissVectorStore(tmp_path, DIM)
    vectors_a = _random_normalized(2, seed=1)
    vectors_b = _random_normalized(2, seed=2)

    await store.add("doc-a", ["a0", "a1"], vectors_a)
    await store.add("doc-b", ["b0", "b1"], vectors_b)

    removed = await store.delete("doc-a")
    assert removed == 2
    assert store.stats()["chunk_count"] == 2
    assert store.stats()["document_count"] == 1

    hits = await store.search(vectors_a[0], top_k=5)
    assert all(hit.document_id == "doc-b" for hit in hits)

    records = await store.get_document("doc-b")
    assert [r.chunk_text for r in records] == ["b0", "b1"]


async def test_delete_not_found(tmp_path: Path) -> None:
    """``delete`` em id inexistente levanta DocumentNotFoundError."""
    store = FaissVectorStore(tmp_path, DIM)
    with pytest.raises(DocumentNotFoundError):
        await store.delete("missing")


async def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    """Salvar e recarregar o índice preserva stats e resultados de busca."""
    store = FaissVectorStore(tmp_path, DIM)
    vectors_a = _random_normalized(2, seed=1)
    vectors_b = _random_normalized(3, seed=2)
    await store.add("doc-a", ["a0", "a1"], vectors_a, metadata={"title": "A"})
    await store.add("doc-b", ["b0", "b1", "b2"], vectors_b, metadata={"title": "B"})
    await store.save()

    hits_before = await store.search(vectors_a[0], top_k=5)

    reloaded = FaissVectorStore(tmp_path, DIM)
    loaded = await reloaded.load()
    assert loaded is True
    assert reloaded.stats() == store.stats()

    hits_after = await reloaded.search(vectors_a[0], top_k=5)
    assert len(hits_after) == len(hits_before)
    assert [h.document_id for h in hits_after] == [h.document_id for h in hits_before]
    assert [h.chunk_idx for h in hits_after] == [h.chunk_idx for h in hits_before]
    for before, after in zip(hits_before, hits_after, strict=True):
        assert after.score == pytest.approx(before.score, abs=1e-5)
        assert after.chunk == before.chunk
        assert after.metadata == before.metadata

    records = await reloaded.get_document("doc-b")
    assert [r.chunk_text for r in records] == ["b0", "b1", "b2"]


async def test_load_missing_returns_false(tmp_path: Path) -> None:
    """Diretório sem artefatos persistidos faz ``load`` retornar False."""
    store = FaissVectorStore(tmp_path, DIM)
    loaded = await store.load()
    assert loaded is False
    assert store.stats()["chunk_count"] == 0
    assert store.stats()["document_count"] == 0


async def test_load_dimension_mismatch_raises(tmp_path: Path) -> None:
    """Carregar índice com dimensão divergente levanta IndexUnavailableError."""
    store = FaissVectorStore(tmp_path, DIM)
    vectors = _random_normalized(1)
    await store.add("doc-a", ["a0"], vectors)
    await store.save()

    mismatched = FaissVectorStore(tmp_path, 256)
    with pytest.raises(IndexUnavailableError):
        await mismatched.load()
