"""Fixtures compartilhadas entre testes."""

from collections.abc import AsyncIterator
from pathlib import Path

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.search.embedder import FakeEmbedder
from app.search.service import SearchService
from app.search.store import FaissVectorStore


@pytest_asyncio.fixture
async def fake_service(tmp_path: Path) -> SearchService:
    """SearchService com FakeEmbedder e store em memória temporária."""
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


@pytest_asyncio.fixture
async def service_client(fake_service: SearchService) -> AsyncIterator[AsyncClient]:
    """AsyncClient apontando para app FastAPI com SearchService fake injetado diretamente."""
    application = create_app(lifespan_override=_noop_lifespan)
    application.state.search_service = fake_service
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest_asyncio.fixture
async def client(fake_service: SearchService) -> AsyncIterator[AsyncClient]:
    """Client httpx assíncrono apontando para o FastAPI em memória."""
    application = create_app(lifespan_override=_noop_lifespan)
    application.state.search_service = fake_service
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


async def _noop_lifespan(app: object) -> AsyncIterator[None]:  # type: ignore[misc]
    """Lifespan vazio para testes — não inicia recursos reais."""
    yield
