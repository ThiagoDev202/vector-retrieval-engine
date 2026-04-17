---
title: Validators no Pydantic v2
source: autoral
language: pt-br
---

# Validators no Pydantic v2

O Pydantic v2 reformulou completamente a API de validação. O decorator `@validator` do v1 foi substituído por `@field_validator`, que recebe o nome do campo como string e exige a anotação `@classmethod`:

```python
from pydantic import BaseModel, field_validator

class Produto(BaseModel):
    preco: float

    @field_validator("preco")
    @classmethod
    def preco_positivo(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Preço deve ser maior que zero")
        return v
```

Para validações que dependem de múltiplos campos ou precisam do objeto já construído, use `@model_validator(mode="after")`. Nesse modo, o método recebe `self` (a instância já validada) e pode acessar qualquer campo:

```python
from pydantic import model_validator

class Intervalo(BaseModel):
    inicio: int
    fim: int

    @model_validator(mode="after")
    def inicio_antes_do_fim(self) -> "Intervalo":
        if self.inicio >= self.fim:
            raise ValueError("inicio deve ser menor que fim")
        return self
```

Diferente do v1, o Pydantic v2 aplica coerção implícita mais agressiva: uma string `"3.14"` é automaticamente convertida para `float` sem `validator`. Para desativar isso num campo específico, use `Annotated[float, Strict()]`. Erros de validação lançam `ValidationError` com detalhes estruturados — útil para retornar respostas 422 bem formatadas no FastAPI.
