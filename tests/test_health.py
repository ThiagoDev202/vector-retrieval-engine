"""Testes do endpoint de health."""

from httpx import AsyncClient


async def test_health_returns_ok(service_client: AsyncClient) -> None:
    response = await service_client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "index_ready" in body
