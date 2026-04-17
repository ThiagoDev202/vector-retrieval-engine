# Vector Retrieval Engine

API REST assíncrona de **busca semântica** sobre um corpus de artigos técnicos. Gera embeddings localmente com [sentence-transformers](https://www.sbert.net/), armazena em [FAISS](https://faiss.ai/) (similaridade cosseno exata) e expõe endpoints documentados sob `/api/v1` com OpenAPI/Swagger.

- Sem dependência de APIs externas (embeddings 100% locais; modelo `paraphrase-multilingual-MiniLM-L12-v2`, 384 dims, multilíngue PT-BR/EN).
- Índice persistido em volume Docker entre reinícios.
- Corpus inicial com 20 artigos técnicos curtos ingestionados automaticamente no primeiro boot.

---

## Arquitetura

```
            ┌──────────────────────────────────────────────┐
            │                FastAPI (ASGI)                │
            │  /api/v1/{health, stats, search, documents}  │
            └───────────────┬──────────────────────────────┘
                            │
                            ▼
                  ┌──────────────────┐
                  │  SearchService   │◄── singleton por processo
                  └──┬────────────┬──┘
                     │            │
          ┌──────────▼──┐    ┌────▼──────────────┐
          │  Embedder   │    │ FaissVectorStore  │
          │  (local HF) │    │ IndexFlatIP + L2  │
          └─────────────┘    │ + metadata JSON   │
                             └────────┬──────────┘
                                      │
                                      ▼
                              data/index/ (volume)
```

Organização do código (layered por feature):

- `app/main.py` — app FastAPI, `lifespan` (carrega modelo, abre índice, faz bootstrap do corpus se vazio), handlers de erro.
- `app/core/` — `config.py` (env vars), `exceptions.py` (erros de domínio), `logging.py` (JSON).
- `app/search/` — `router.py`, `service.py`, `embedder.py`, `store.py`, `chunking.py`, `ingestion.py`, `schemas.py`.
- `data/raw/` — corpus bundled em Markdown com front-matter (`title`, `source`, `language`).
- `data/index/` — artefatos FAISS + metadados (montado como volume; não versionado).

---

## Quickstart (Docker)

```bash
cp .env.example .env
docker compose up --build
```

No primeiro boot, a imagem é construída (~2 min), o modelo HF é baixado durante o build e o corpus é ingestionado no startup. A API fica disponível em:

> **Ambientes offline / air-gapped:** se o build/container não alcançar `huggingface.co`, use
> `docker compose build --build-arg PREFETCH_MODEL=0` (a imagem fica válida e tenta baixar no
> startup). Para uso 100% offline, monte um cache HF pré-populado no host em
> `~/.cache/huggingface/` como volume adicional para `/opt/hf-cache` no serviço do
> `docker-compose.yml`, e defina `HF_HUB_OFFLINE=1` no `.env`.


- **API:** http://localhost:8000/api/v1
- **Swagger UI:** http://localhost:8000/docs

Boots subsequentes reutilizam o volume `vector-retrieval-engine_vector-data` — o índice é recarregado sem re-embeddar.

---

## Endpoints

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/v1/health` | liveness + readiness do índice |
| `GET` | `/api/v1/stats` | contagem de documentos/chunks, modelo e dimensão |
| `POST` | `/api/v1/search` | busca semântica por query textual |
| `POST` | `/api/v1/documents` | indexa novo documento |
| `GET` | `/api/v1/documents/{id}` | retorna documento + chunks |
| `DELETE` | `/api/v1/documents/{id}` | remove documento do índice |

---

## Exemplos de uso

### Verificar status

```bash
curl -s http://localhost:8000/api/v1/stats | jq
```

```json
{
  "document_count": 20,
  "chunk_count": 34,
  "embedding_model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
  "dimension": 384
}
```

### 3 consultas de demonstração

O modelo é multilíngue, então consultas em PT-BR e EN funcionam sobre o mesmo corpus.

**1) PT-BR — pergunta sobre async:**

```bash
curl -s -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "como usar async await em FastAPI", "top_k": 3}' | jq
```

Top hit esperado: `fastapi-async-basics` (score típico > 0.6), seguido de `asyncio-lock-patterns` ou `httpx-async-client`.

**2) EN — pergunta sobre similaridade:**

```bash
curl -s -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "what is cosine similarity and why it matters", "top_k": 3}' | jq
```

Top hit esperado: `cosine-similarity`; secundários possíveis: `faiss-index-types`, `embeddings-overview`.

**3) PT-BR — tooling:**

```bash
curl -s -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "gerenciamento de dependências com uv", "top_k": 3}' | jq
```

Top hit esperado: `uv-package-manager`; secundário provável: `poetry-vs-uv`.

### Indexar um novo documento

```bash
curl -s -X POST http://localhost:8000/api/v1/documents \
  -H "Content-Type: application/json" \
  -d '{
    "id": "minha-nota",
    "content": "asyncio.Lock protege seções críticas em código assíncrono Python.",
    "metadata": {"title": "Minha nota", "source": "manual"}
  }' | jq
```

```json
{ "document_id": "minha-nota", "chunk_count": 1, "dimension": 384 }
```

### Buscar documento por ID

```bash
curl -s http://localhost:8000/api/v1/documents/minha-nota | jq
```

### Remover documento

```bash
curl -s -X DELETE http://localhost:8000/api/v1/documents/minha-nota -o /dev/null -w "%{http_code}\n"
# 204
```

---

## Variáveis de ambiente

Todas têm default seguro; basta copiar `.env.example` para `.env`.

| Variável | Default | Descrição |
|---|---|---|
| `APP_ENV` | `dev` | ambiente de execução |
| `EMBEDDING_MODEL` | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | model id do HuggingFace |
| `EMBEDDING_DIM` | `384` | dimensão do vetor (validada contra o modelo) |
| `INDEX_DIR` | `/app/data/index` | onde FAISS persiste o índice |
| `CORPUS_DIR` | `/app/data/raw` | corpus Markdown para bootstrap |
| `CHUNK_SIZE` | `256` | tokens por chunk |
| `CHUNK_OVERLAP` | `32` | sobreposição entre chunks |
| `DEFAULT_TOP_K` | `5` | `top_k` default em `/search` |
| `BOOTSTRAP_ON_STARTUP` | `true` | ingere o corpus se o índice estiver vazio |

---

## Desenvolvimento local (sem Docker)

```bash
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

O primeiro boot baixa o modelo HF (~80 MB) em `~/.cache/huggingface`.

### Gates de qualidade

Rodam localmente e no CI:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run pytest -v --cov=app --cov-report=term-missing
```

Cobertura mínima: **85%** em `app/search/`. Todos os testes usam `FakeEmbedder` determinístico — nenhum download da HuggingFace acontece em CI.

---

## Como funciona

1. **Ingestão** — cada `.md` em `data/raw/` é parseado (front-matter simples `key: value`), dividido em chunks de até 256 tokens com overlap de 32, e embeddado pelo modelo multilíngue.
2. **Armazenamento** — vetores L2-normalizados são adicionados a um `faiss.IndexFlatIP`; metadados (document_id, chunk_idx, texto original, front-matter) ficam em `metadata.json`; os próprios vetores são salvos em `vectors.npy` para permitir `DELETE` com rebuild parcial sem re-embeddar.
3. **Busca** — a query é embeddada + normalizada; `IndexFlatIP.search` retorna os `top_k` chunks mais similares (cosseno = produto interno de vetores L2-normalizados).

---

## Performance

Alvos oficiais (PRD):

- `POST /search` p95 **< 100 ms** (corpus ≤ 1000 chunks, modelo real, CPU x86_64 moderno).
- Cold-start com índice persistido **< 5 s**; com ingestão do corpus bundled **< 30 s**.

### Benchmark offline

O teste `tests/test_benchmark.py` executa 100 buscas contra um `FakeEmbedder` (vetores determinísticos) com 200 documentos sintéticos indexados, e reporta p50/p95/p99:

```bash
uv run pytest tests/test_benchmark.py -v -s
```

Esse benchmark **não** usa o modelo real — mede apenas o overhead da pipeline HTTP + chunking + store + search. Resultado típico em CPU moderna: p95 < 10 ms. O gargalo em produção é o `embedder.encode()` (~60-90 ms por query no modelo `paraphrase-multilingual-MiniLM-L12-v2` em CPU).

Para medir com o modelo real, é preciso rodar em ambiente com acesso a HuggingFace (veja seção "Ambientes offline") e substituir o `FakeEmbedder` no teste por uma instância real. Não entra no CI por custo de download.

---

## Limitações conhecidas (MVP)

- Índice in-process: escala limitada pela memória do container. Para corpora > 100k chunks considere migrar para `IndexIVFFlat` ou Milvus.
- `DELETE` faz rebuild parcial do índice (O(n)); aceitável para este tamanho de corpus.
- Sem autenticação — assumir deploy em rede privada ou atrás de gateway/API gateway.
- Sem re-ranking por cross-encoder — resultados são do bi-encoder direto.
- `top_k` é limitado a 50 por request (validação Pydantic em `SearchQuery`).
- Histórico de conversa/sessão não aplicável — cada request é independente.

---

## Auditoria de dependências

A árvore de dependências pode ser auditada contra o banco CVE público (PyPI Advisory DB) via `pip-audit`, incluído como dev-dep:

```bash
uv run pip-audit --strict
```

- `--strict` promove warnings a erros — falha a execução quando há CVE.

### CVEs aceitas

| Pacote | Versão | CVE | Motivo |
|---|---|---|---|
| `transformers` | 4.57.x | CVE-2026-1839 | Fix disponível apenas em `5.0.0rc3` (release candidate). O caminho vulnerável não é exercitado pelo `SentenceTransformerEmbedder` (usamos apenas `encode` com `normalize_embeddings=True`); nenhum teste dispara. Reavaliar quando `5.0.0` estável for publicado. |

O hook pre-commit `pip-audit` está cadastrado em stage manual (não roda em `git commit`). Execute explicitamente quando quiser:

```bash
uv run pre-commit run pip-audit --hook-stage manual --all-files
```

Quando uma CVE crítica ou alta aparecer, a correção padrão é bump de versão em `pyproject.toml` seguido de `uv lock --upgrade-package <nome>`. CVEs classificadas como "low" podem ser documentadas como aceitas se a função vulnerável não for usada no nosso caminho.

---

## Estrutura do projeto

```
vector-retrieval-engine/
├── app/
│   ├── main.py
│   ├── core/           (config, exceptions, logging)
│   └── search/         (router, service, embedder, store, chunking, ingestion, schemas)
├── data/
│   ├── raw/            (20 artigos .md bundled)
│   └── index/          (volume Docker; faiss.index, metadata.json, vectors.npy)
├── tests/              (62 testes)
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── .env.example
```

---

## Licença e créditos

Projeto de estudo/portfolio. Modelo `paraphrase-multilingual-MiniLM-L12-v2` sob licença Apache 2.0 (ver HuggingFace). FAISS sob licença MIT.
