"""Testes unitários do SearchService com FakeEmbedder."""

from pathlib import Path

import pytest
import pytest_asyncio

from app.search.embedder import FakeEmbedder
from app.search.schemas import DocumentIn, SearchQuery
from app.search.service import SearchService
from app.search.store import FaissVectorStore


@pytest_asyncio.fixture
async def service(tmp_path: Path) -> SearchService:
    """SearchService com FakeEmbedder e store temporário."""
    embedder = FakeEmbedder(dimension=384)
    store = FaissVectorStore(tmp_path / "index", dimension=384)
    return SearchService(
        embedder=embedder,
        store=store,
        chunk_size=32,
        chunk_overlap=4,
        default_top_k=3,
        embedding_model_name="fake",
    )


async def test_add_document_generates_id_if_none(service: SearchService) -> None:
    payload = DocumentIn(id=None, content="Texto para teste de geração de ID automático")
    result = await service.add_document(payload)
    assert result.document_id
    assert len(result.document_id) > 0


async def test_add_document_respects_custom_id(service: SearchService) -> None:
    payload = DocumentIn(id="meu-doc", content="Texto de teste com ID personalizado")
    result = await service.add_document(payload)
    assert result.document_id == "meu-doc"


async def test_add_document_rejects_empty_after_chunking(service: SearchService) -> None:
    payload = DocumentIn(id=None, content="   ")
    with pytest.raises(ValueError, match="conteúdo vazio após tokenização"):
        await service.add_document(payload)


async def test_add_document_persists(service: SearchService, tmp_path: Path) -> None:
    payload = DocumentIn(id="doc-persist", content="Texto para testar persistência em disco")
    await service.add_document(payload)
    index_file = tmp_path / "index" / "faiss.index"
    assert index_file.exists()


async def test_delete_document_persists(service: SearchService, tmp_path: Path) -> None:
    payload = DocumentIn(id="doc-del", content="Documento que será deletado para testar")
    await service.add_document(payload)
    await service.delete_document("doc-del")
    index_file = tmp_path / "index" / "faiss.index"
    assert index_file.exists()


async def test_search_uses_default_top_k_when_none(service: SearchService) -> None:
    for i in range(5):
        await service.add_document(
            DocumentIn(id=f"doc-{i}", content=f"Documento número {i} com conteúdo distinto")
        )
    query = SearchQuery(query="documento conteúdo", top_k=None)
    result = await service.search(query)
    assert len(result.hits) <= 3


async def test_get_document_returns_aggregated_metadata(service: SearchService) -> None:
    await service.add_document(
        DocumentIn(id="x", content="texto curto", metadata={"k": "v"}),
    )
    result = await service.get_document("x")
    assert result.metadata == {"k": "v"}
