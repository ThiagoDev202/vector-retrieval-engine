---
title: "Ruff: a single tool for lint and format"
source: autoral
language: en
---

# Ruff: a single tool for lint and format

Ruff is a Python linter and formatter shipped as a single compiled binary written in Rust. It replaces a typical setup that would include flake8, isort, pyupgrade, and Black — with faster execution and a unified configuration block in `pyproject.toml`.

Rule sets are opt-in. A practical starting configuration enables:

```toml
[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]
```

- `E`/`F`: pycodestyle and Pyflakes errors (undefined names, unused imports)
- `I`: import ordering (replaces isort)
- `UP`: pyupgrade — rewrites deprecated syntax for the target Python version
- `B`: flake8-bugbear — catches common logic bugs
- `SIM`: flake8-simplify — suggests idiomatic rewrites

For formatting, `ruff format` follows Black's style with virtually identical output. Unlike Black, it runs in milliseconds even on large codebases. To integrate with pre-commit, add it as a hook with `ruff check --fix` for auto-fixable issues and `ruff format --check` for CI enforcement (exit non-zero if formatting differs). Running both lint and format in one pre-commit pass keeps the feedback loop tight.
