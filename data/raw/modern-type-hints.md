---
title: Type hints modernos em Python
source: autoral
language: pt-br
---

# Type hints modernos em Python

Desde o Python 3.10, a sintaxe de type hints ficou mais enxuta e expressiva. Conhecer as formas modernas evita importações desnecessárias e torna as anotações mais legíveis.

**Generics embutidos**: antes do 3.9, era obrigatório importar `List`, `Dict`, `Tuple` de `typing`. Agora, os tipos built-in aceitam parâmetros diretamente:

```python
# Antigo
from typing import List, Optional
def process(items: List[str]) -> Optional[int]: ...

# Moderno (3.10+)
def process(items: list[str]) -> int | None: ...
```

**`TypeAlias`** (3.10) e **`type`** (3.12) declaram aliases explícitos, evitando que mypy confunda um alias com uma reatribuição de variável:

```python
from typing import TypeAlias
Vector: TypeAlias = list[float]
```

**`Protocol`** substitui herança para duck typing estático. Qualquer classe que implemente os métodos exigidos satisfaz o Protocol sem precisar herdar dele — útil para definir interfaces sem acoplar módulos:

```python
from typing import Protocol

class Readable(Protocol):
    def read(self) -> str: ...
```

**`ParamSpec`** captura a assinatura completa de uma função para decorators que precisam preservar o tipo dos argumentos:

```python
from typing import Callable, ParamSpec, TypeVar
P = ParamSpec("P")
R = TypeVar("R")

def logged(fn: Callable[P, R]) -> Callable[P, R]:
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        print(f"calling {fn.__name__}")
        return fn(*args, **kwargs)
    return wrapper
```

Sem `ParamSpec`, o decorator apagaria os tipos dos argumentos da função decorada.
