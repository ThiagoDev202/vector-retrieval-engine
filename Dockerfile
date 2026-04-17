# syntax=docker/dockerfile:1.7

ARG PYTHON_VERSION=3.12
ARG EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2

# ---------- Builder ----------
FROM python:${PYTHON_VERSION}-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /usr/local/bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    HF_HOME=/opt/hf-cache \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Resolução de dependências em camada separada para aproveitar cache.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

# Pré-download opcional do modelo HF. Se o build não tiver acesso a huggingface.co,
# a imagem ainda fica válida — o modelo é baixado no primeiro startup.
ARG EMBEDDING_MODEL
ARG PREFETCH_MODEL=1
RUN mkdir -p /opt/hf-cache && \
    if [ "$PREFETCH_MODEL" = "1" ]; then \
      /opt/venv/bin/python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('${EMBEDDING_MODEL}')" \
      || echo "aviso: pré-download do modelo falhou; será baixado no startup"; \
    fi

# Instala o projeto em si (copia mínima para invalidar cache só quando o código muda).
COPY app ./app
RUN uv sync --frozen --no-dev

# ---------- Runtime ----------
FROM python:${PYTHON_VERSION}-slim AS runtime

ENV PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/opt/hf-cache \
    APP_ENV=prod

WORKDIR /app

# venv + cache do modelo vêm do builder; usuário não-root.
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /opt/hf-cache /opt/hf-cache

COPY app ./app
COPY data/raw ./data/raw

RUN mkdir -p /app/data/index && \
    useradd --system --uid 1001 --gid 0 --home-dir /app app && \
    chown -R app:0 /app /opt/venv /opt/hf-cache

USER app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
