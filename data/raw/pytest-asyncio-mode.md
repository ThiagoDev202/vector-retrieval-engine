---
title: pytest-asyncio auto mode explained
source: autoral
language: en
---

# pytest-asyncio auto mode explained

`pytest-asyncio` lets pytest discover and run `async def` test functions. By default it requires every async test to carry a `@pytest.mark.asyncio` decorator, which becomes repetitive in large test suites. Setting `asyncio_mode = "auto"` in `pyproject.toml` removes that requirement:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

With auto mode active, any `async def test_*` function is automatically treated as an asyncio coroutine without an explicit marker. This also applies to `async def` fixtures — though those must still use `@pytest_asyncio.fixture` rather than `@pytest.fixture`:

```python
import pytest_asyncio
from httpx import AsyncClient

@pytest_asyncio.fixture
async def client(app):
    async with AsyncClient(app=app, base_url="http://test") as c:
        yield c
```

Using plain `@pytest.fixture` on an async fixture under auto mode raises a `PytestUnraisableExceptionWarning` in newer versions and silently misbehaves in older ones.

A known pitfall is event loop scope. By default each test gets its own event loop, so state stored in module-level coroutines is not shared. If you need a shared loop across a test session (e.g., a persistent database connection), set `loop_scope = "session"` on the fixture. Be careful: this can hide ordering-dependent bugs if tests mutate shared state.

Mixing sync and async fixtures in the same test is safe — pytest-asyncio bridges the call correctly — but mixing `asyncio` and `trio` backends in the same process is not supported without a backend-isolating plugin.
