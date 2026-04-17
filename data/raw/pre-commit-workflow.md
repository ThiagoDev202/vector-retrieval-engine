---
title: Workflow com pre-commit
source: autoral
language: pt-br
---

# Workflow com pre-commit

`pre-commit` é um gerenciador de hooks Git que executa verificações automaticamente antes de cada commit (ou push). Ele isola cada hook em seu próprio ambiente virtual, garantindo reprodutibilidade independente do ambiente local do desenvolvedor.

**Instalação e ativação**:

```bash
uv add --dev pre-commit
uv run pre-commit install          # instala o hook em .git/hooks/pre-commit
uv run pre-commit install --hook-type pre-push  # também instala pre-push
```

A separação entre os dois tipos de hook é estratégica: o hook `pre-commit` deve conter apenas verificações **rápidas** (lint, format, type-check), que completam em segundos. Já o hook `pre-push` pode conter verificações **lentas** como a suíte de testes completa — toleráveis antes de enviar código ao remoto, mas irritantes a cada commit local.

Exemplo de `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: ruff-check
        name: ruff check
        entry: uv run ruff check .
        language: system
        pass_filenames: false
      - id: mypy
        name: mypy
        entry: uv run mypy app
        language: system
        pass_filenames: false
        stages: [pre-push]
```

**Espelhando hooks no CI**: o pipeline de CI deve rodar os mesmos comandos dos hooks, na mesma ordem. Isso elimina a divergência entre o que passa localmente e o que quebra no servidor. Uma forma simples é usar `pre-commit run --all-files` no CI em vez de duplicar cada step — mas verifique se os stages (`pre-commit` vs. `pre-push`) estão sendo considerados corretamente com a flag `--hook-stage`.
