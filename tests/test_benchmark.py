"""Benchmark offline da pipeline HTTP de busca (FakeEmbedder)."""

import os
import statistics
import time

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.benchmark]


@pytest.mark.skipif(os.getenv("SKIP_BENCHMARK") == "1", reason="benchmark desabilitado")
async def test_search_p95_under_threshold_with_fake_embedder(
    service_client: AsyncClient,
) -> None:
    """Mede p50/p95/p99 de /search com FakeEmbedder e 200 docs sintéticos."""
    # Ingere 200 docs sintéticos
    for i in range(200):
        content = (
            f"documento numero {i} sobre tema {i % 10}. "
            "texto filler para chunking em varios chunks com palavras suficientes "
            "para garantir que o chunker produza pelo menos um chunk de tamanho "
            f"razoavel e o embedder gere vetores deterministicos para o indice {i}."
        )
        response = await service_client.post(
            "/api/v1/documents",
            json={"id": f"bench-{i}", "content": content, "metadata": {"idx": i}},
        )
        assert response.status_code == 201

    # Warmup: 10 queries descartadas
    for _ in range(10):
        warmup = await service_client.post(
            "/api/v1/search", json={"query": "texto filler tema", "top_k": 5}
        )
        assert warmup.status_code == 200

    # Medição: 100 iterações
    latencies_ms: list[float] = []
    for _ in range(100):
        start = time.perf_counter()
        response = await service_client.post(
            "/api/v1/search", json={"query": "texto filler tema", "top_k": 5}
        )
        end = time.perf_counter()
        assert response.status_code == 200
        latencies_ms.append((end - start) * 1000.0)

    p50 = statistics.median(latencies_ms)
    p95 = statistics.quantiles(latencies_ms, n=20)[18]  # 95th percentile
    p99 = statistics.quantiles(latencies_ms, n=100)[98]

    print(
        f"\n[bench] /search top_k=5 (FakeEmbedder, 200 docs): "
        f"p50={p50:.2f}ms p95={p95:.2f}ms p99={p99:.2f}ms"
    )

    # threshold relaxed for slow CI runners
    assert p95 < 100.0, f"p95={p95:.2f}ms excedeu o limite de 100ms"
