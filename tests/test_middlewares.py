"""Testes para middlewares e exception handlers de app/main.py."""

import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.main import create_app
from app.search.embedder import FakeEmbedder
from app.search.service import SearchService
from app.search.store import FaissVectorStore


async def _noop_lifespan(app: object) -> AsyncIterator[None]:  # type: ignore[misc]
    """Lifespan vazio para testes."""
    yield


@pytest_asyncio.fixture
async def fake_service(tmp_path: Path) -> SearchService:
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


@pytest_asyncio.fixture
async def service_client(fake_service: SearchService) -> AsyncIterator[AsyncClient]:
    """Client padrão (app_env=dev por default)."""
    application = create_app(lifespan_override=_noop_lifespan)
    application.state.search_service = fake_service
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest_asyncio.fixture
async def prod_client(fake_service: SearchService) -> AsyncIterator[AsyncClient]:
    """Client com app_env=prod para verificar supressão de detalhes."""
    get_settings.cache_clear()
    original = os.environ.get("APP_ENV")
    os.environ["APP_ENV"] = "prod"
    get_settings.cache_clear()
    try:
        application = create_app(lifespan_override=_noop_lifespan)
        application.state.search_service = fake_service
        transport = ASGITransport(app=application)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            yield ac
    finally:
        if original is None:
            os.environ.pop("APP_ENV", None)
        else:
            os.environ["APP_ENV"] = original
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_cors_headers_present_in_options(service_client: AsyncClient) -> None:
    """Resposta a OPTIONS deve conter o header access-control-allow-origin."""
    response = await service_client.options(
        "/api/v1/search",
        headers={"Origin": "http://example.com", "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" in response.headers


@pytest.mark.asyncio
async def test_body_size_limit_rejects_oversized(service_client: AsyncClient) -> None:
    """POST com Content-Length acima de 1 MiB deve retornar 413."""
    # Envia corpo real de 1.1 MiB para garantir que o middleware detecta
    big_body = b"x" * (1_048_576 + 1024)
    response = await service_client.post(
        "/api/v1/documents",
        content=big_body,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 413
    assert response.json()["detail"] == "payload excede o tamanho máximo de 1 MiB"


@pytest.mark.asyncio
async def test_body_size_limit_accepts_small(service_client: AsyncClient) -> None:
    """POST com payload pequeno não deve ser bloqueado pelo middleware de tamanho."""
    payload = {"document_id": "doc-1", "text": "conteúdo de teste pequeno"}
    response = await service_client.post("/api/v1/documents", json=payload)
    # 201 Created ou outro status da aplicação (não 413)
    assert response.status_code != 413


@pytest.mark.asyncio
async def test_document_not_found_dev_has_extra_info(service_client: AsyncClient) -> None:
    """Em dev, 404 deve trazer detail fixo e document_id no corpo."""
    response = await service_client.get("/api/v1/documents/nao-existe")
    assert response.status_code == 404
    body = response.json()
    assert body["detail"] == "documento não encontrado"
    assert body.get("document_id") == "nao-existe"


@pytest.mark.asyncio
async def test_document_not_found_prod_minimal(prod_client: AsyncClient) -> None:
    """Em prod, 404 deve conter apenas detail, sem document_id."""
    # NOTE: prod-mode handler behavior exercised manually via APP_ENV=prod
    response = await prod_client.get("/api/v1/documents/nao-existe")
    assert response.status_code == 404
    body = response.json()
    assert body["detail"] == "documento não encontrado"
    assert "document_id" not in body
