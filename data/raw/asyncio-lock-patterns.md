---
title: Padrões com asyncio.Lock
source: autoral
language: pt-br
---

# Padrões com asyncio.Lock

`asyncio.Lock` é o mecanismo de exclusão mútua para código assíncrono em Python. Diferente de `threading.Lock`, ele não bloqueia a thread — ao aguardar a aquisição do lock, o event loop pode processar outras corrotinas.

O caso de uso clássico em FastAPI é proteger um dicionário compartilhado (como um store in-memory) contra race conditions entre requests concorrentes:

```python
import asyncio

_store: dict[str, list] = {}
_lock = asyncio.Lock()

async def get_or_create(session_id: str) -> list:
    async with _lock:
        if session_id not in _store:
            _store[session_id] = []
        return _store[session_id]
```

**Lock por instância vs. lock global**: um lock global protege todo o dicionário mas serializa todos os acessos, mesmo que sejam para chaves diferentes. Para alta concorrência, considere um lock por chave (`dict[str, asyncio.Lock]`) — mas isso aumenta a complexidade de criação e limpeza do lock.

Evite adquirir `asyncio.Lock` dentro de trechos CPU-bound (como laços de processamento pesado). Se a seção crítica demorar, as outras corrotinas ficam represadas mesmo sem I/O. Nesse caso, delegue o trabalho pesado a `asyncio.to_thread` ou `ProcessPoolExecutor` antes de entrar na seção protegida.

`threading.Lock` nunca deve ser usado em código async: ao chamar `acquire()` de forma bloqueante, você congela o event loop inteiro, anulando o benefício do I/O assíncrono.
