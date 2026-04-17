---
title: Docker multi-stage builds for Python
source: autoral
language: en
---

# Docker multi-stage builds for Python

A multi-stage Dockerfile separates the build environment (where dependencies are compiled and installed) from the runtime image (what actually runs in production). This keeps the final image lean by excluding compilers, build headers, and caches that are only needed during installation.

```dockerfile
FROM python:3.12-slim AS builder
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen --no-dev

FROM python:3.12-slim AS runtime
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY app/ ./app/
ENV PATH="/app/.venv/bin:$PATH"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

The key is `COPY --from=builder /app/.venv /app/.venv`: only the populated virtual environment crosses the stage boundary. The runtime stage never needs `pip`, `uv`, or any compiler. With `python:3.12-slim` as the base for the runtime stage, the resulting image typically sits under 200 MB even for projects with several transitive dependencies.

For applications that need ML model weights, download them in the builder stage and copy the cache directory across — this avoids re-downloading at container startup. Use `--no-dev` (or `--no-dev-dependencies`) during `uv sync` in the builder to exclude test and lint tooling from the installed environment.
