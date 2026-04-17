---
title: httpx.AsyncClient for testing FastAPI
source: autoral
language: en
---

# httpx.AsyncClient for testing FastAPI

FastAPI's built-in `TestClient` wraps Starlette's synchronous test client, which runs your async app inside a thread. That works fine for simple smoke tests, but it cannot share an asyncio event loop with async fixtures — which matters when your test setup uses `async with`, async database connections, or async locks.

`httpx.AsyncClient` with `ASGITransport` solves this by calling the ASGI app directly in-process, within the same event loop as the test:

```python
from httpx import AsyncClient, ASGITransport
from app.main import app

async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
    assert response.status_code == 200
```

The `base_url` parameter is required by httpx but is never actually used for a network connection — it only populates the `Host` header and the `url` attribute on the response. The convention `http://test` or `http://testserver` is common; the value does not matter as long as it is a valid URL.

Regarding lifespan events: `ASGITransport` does **not** trigger FastAPI's `lifespan` context manager by default. If your app registers startup/shutdown handlers via `@asynccontextmanager` lifespan, wrap the client inside an `asgi_lifespan` helper or use `httpx-asgi` lifespan support. With plain `ASGITransport`, startup code runs only when the first request arrives.

For test isolation, override dependencies with `app.dependency_overrides` before each test and clear overrides in teardown to avoid leaking state between tests.
