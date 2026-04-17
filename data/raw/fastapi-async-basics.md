---
title: FastAPI e async/await na prática
source: autoral
language: pt-br
---

# FastAPI e async/await na prática

FastAPI foi projetado para trabalhar com o modelo de concorrência do Python moderno. Quando você declara um endpoint com `async def`, o Uvicorn (servidor ASGI) consegue processar outras requisições enquanto aguarda operações de I/O — chamadas de rede, acesso a banco de dados, integração com LLMs.

```python
@app.get("/usuario/{id}")
async def obter_usuario(id: int, db: AsyncSession = Depends(get_db)) -> UsuarioResponse:
    return await db.get(Usuario, id)
```

A armadilha mais comum é chamar código síncrono bloqueante dentro de uma função `async def`. Bibliotecas como `requests` ou operações de leitura de arquivo com `open()` bloqueiam a event loop inteira, anulando o benefício da assincronia. Nesses casos, use `asyncio.to_thread()` para delegar a operação a uma thread separada:

```python
import asyncio

async def ler_arquivo(caminho: str) -> str:
    conteudo = await asyncio.to_thread(open(caminho).read)
    return conteudo
```

Use `def` simples (síncrono) quando o handler não faz I/O — FastAPI executa funções síncronas em um threadpool automaticamente, evitando que bloqueiem a event loop. A regra prática: se o handler aguarda algo externo, use `async def` com `await`; se apenas processa dados em memória e é rápido, `def` é suficiente e igualmente correto.
