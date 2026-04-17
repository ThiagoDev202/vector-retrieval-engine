"""Testes de integração dos endpoints do router de busca semântica."""

from httpx import AsyncClient


async def test_health(service_client: AsyncClient) -> None:
    response = await service_client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["index_ready"] is True


async def test_stats_empty(service_client: AsyncClient) -> None:
    response = await service_client.get("/api/v1/stats")
    assert response.status_code == 200
    body = response.json()
    assert body["document_count"] == 0
    assert body["chunk_count"] == 0
    assert body["embedding_model"] == "fake"
    assert body["dimension"] == 384


async def test_create_document(service_client: AsyncClient) -> None:
    payload = {"content": "Python é uma linguagem de programação interpretada"}
    response = await service_client.post("/api/v1/documents", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["document_id"]
    assert body["chunk_count"] >= 1
    assert body["dimension"] == 384


async def test_create_document_invalid(service_client: AsyncClient) -> None:
    payload = {"content": ""}
    response = await service_client.post("/api/v1/documents", json=payload)
    assert response.status_code == 422


async def test_create_document_custom_id(service_client: AsyncClient) -> None:
    payload = {"id": "my-doc", "content": "Conteúdo de teste para documento com ID personalizado"}
    response = await service_client.post("/api/v1/documents", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["document_id"] == "my-doc"


async def test_search(service_client: AsyncClient) -> None:
    await service_client.post(
        "/api/v1/documents",
        json={"id": "doc-a", "content": "Python é uma linguagem de programação de alto nível"},
    )
    await service_client.post(
        "/api/v1/documents",
        json={"id": "doc-b", "content": "O Brasil é um país da América do Sul"},
    )
    response = await service_client.post(
        "/api/v1/search",
        json={"query": "linguagem de programação Python"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "linguagem de programação Python"
    assert isinstance(body["hits"], list)
    assert len(body["hits"]) >= 1
    for hit in body["hits"]:
        assert hit["document_id"] in {"doc-a", "doc-b"}
        assert hit["chunk"]
        assert isinstance(hit["score"], float)


async def test_search_top_k_override(service_client: AsyncClient) -> None:
    await service_client.post(
        "/api/v1/documents",
        json={"id": "doc-x", "content": "FastAPI é um framework web moderno para Python"},
    )
    await service_client.post(
        "/api/v1/documents",
        json={"id": "doc-y", "content": "Django é outro framework web popular para Python"},
    )
    response = await service_client.post(
        "/api/v1/search",
        json={"query": "framework web Python", "top_k": 1},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["hits"]) <= 1


async def test_get_document(service_client: AsyncClient) -> None:
    await service_client.post(
        "/api/v1/documents",
        json={"id": "doc-detail", "content": "Conteúdo para verificação de detalhes do documento"},
    )
    response = await service_client.get("/api/v1/documents/doc-detail")
    assert response.status_code == 200
    body = response.json()
    assert body["document_id"] == "doc-detail"
    assert isinstance(body["chunks"], list)
    assert len(body["chunks"]) >= 1
    for chunk in body["chunks"]:
        assert "chunk_idx" in chunk
        assert "text" in chunk
        assert "metadata" in chunk


async def test_get_document_not_found(service_client: AsyncClient) -> None:
    response = await service_client.get("/api/v1/documents/nao-existe")
    assert response.status_code == 404
    body = response.json()
    assert "detail" in body
    assert body["detail"]


async def test_delete_document(service_client: AsyncClient) -> None:
    await service_client.post(
        "/api/v1/documents",
        json={"id": "doc-del", "content": "Documento que será deletado em seguida"},
    )
    response = await service_client.delete("/api/v1/documents/doc-del")
    assert response.status_code == 204

    get_response = await service_client.get("/api/v1/documents/doc-del")
    assert get_response.status_code == 404
