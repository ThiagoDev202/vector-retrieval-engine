# Vector Retrieval Engine

API REST assíncrona de busca semântica construída com **FastAPI + sentence-transformers + FAISS**.

> Documentação completa e quickstart serão adicionados ao final da implementação (fase 7).

## Requisitos

- Python 3.12
- [uv](https://docs.astral.sh/uv/) para dependências
- Docker + Docker Compose (para subir o serviço)

## Desenvolvimento

```bash
uv sync
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run pytest
```

## Status

Em implementação faseada — veja o roadmap interno.
