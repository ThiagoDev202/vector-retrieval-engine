"""Testes para hierarquia de exceções e seus handlers HTTP."""

from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.exceptions import DocumentNotFoundError, EmbeddingError, IndexUnavailableError
from app.main import register_exception_handlers


def _make_app_with_routes() -> FastAPI:
    """Cria FastAPI de teste com handlers e rotas que levantam exceções de domínio."""
    test_app = FastAPI()
    register_exception_handlers(test_app)

    @test_app.get("/raise/document-not-found")
    async def raise_document_not_found() -> None:
        raise DocumentNotFoundError("abc123")

    @test_app.get("/raise/index-unavailable")
    async def raise_index_unavailable() -> None:
        raise IndexUnavailableError("índice corrompido")

    @test_app.get("/raise/embedding-error")
    async def raise_embedding_error() -> None:
        raise EmbeddingError("falha ao codificar texto")

    return test_app


@pytest.fixture
async def test_client() -> AsyncIterator[AsyncClient]:
    """Client httpx apontando para app de teste isolado."""
    application = _make_app_with_routes()
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


def test_document_not_found_error_has_document_id() -> None:
    """Verifica que DocumentNotFoundError expõe document_id como atributo."""
    exc = DocumentNotFoundError("abc")
    assert exc.document_id == "abc"
    assert "abc" in str(exc)


async def test_document_not_found_returns_404(test_client: AsyncClient) -> None:
    """DocumentNotFoundError deve resultar em HTTP 404 com detail em PT-BR."""
    response = await test_client.get("/raise/document-not-found")
    assert response.status_code == 404
    body = response.json()
    assert "detail" in body
    assert "abc123" in body["detail"]


async def test_index_unavailable_returns_503(test_client: AsyncClient) -> None:
    """IndexUnavailableError deve resultar em HTTP 503."""
    response = await test_client.get("/raise/index-unavailable")
    assert response.status_code == 503
    body = response.json()
    assert "detail" in body


async def test_embedding_error_returns_500(test_client: AsyncClient) -> None:
    """EmbeddingError deve resultar em HTTP 500."""
    response = await test_client.get("/raise/embedding-error")
    assert response.status_code == 500
    body = response.json()
    assert "detail" in body
