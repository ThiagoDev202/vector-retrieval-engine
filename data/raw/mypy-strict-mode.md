---
title: Mypy no modo estrito
source: autoral
language: pt-br
---

# Mypy no modo estrito

Ativar `strict = true` no `pyproject.toml` habilita um conjunto amplo de verificações que o mypy mantém desligadas por padrão. As mais relevantes são `disallow_untyped_defs` (proíbe funções sem anotações de retorno e parâmetros), `disallow_any_generics` (exige parâmetros de tipo em genéricos como `list[str]` ao invés de `list`) e `warn_return_any`.

```toml
[tool.mypy]
strict = true
python_version = "3.12"
```

Um problema frequente ao adotar o modo estrito em projetos reais é que muitas bibliotecas de terceiros não distribuem stubs de tipos. Para essas, use `ignore_missing_imports` por módulo — evite ativar a opção globalmente, pois ela oculta erros reais:

```ini
[[tool.mypy.overrides]]
module = ["faiss", "sentence_transformers"]
ignore_missing_imports = true
```

Evite `# type: ignore` sem uma explicação explícita. Quando necessário, prefira a forma `# type: ignore[attr-defined]` com o código do erro, que documenta exatamente o que está sendo suprimido e permite que ferramentas futuras identifiquem o ponto de abandono. O uso de `Any` deve ser restrito a fronteiras de integração com código não tipado — nunca em lógica de domínio. Mypy estrito em conjunto com Ruff e testes garante que refatorações não quebrem contratos implícitos.
