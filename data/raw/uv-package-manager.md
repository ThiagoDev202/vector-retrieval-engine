---
title: Why uv replaces pip and Poetry
source: autoral
language: en
---

# Why uv replaces pip and Poetry

`uv` is a Python package manager written in Rust, developed by Astral (the same team behind Ruff). Its resolver and installer are orders of magnitude faster than pip — benchmarks consistently show 10–100x speedups for cold installs, largely because dependency resolution runs in parallel and the binary avoids Python startup overhead.

The tool is compatible with PEP 621 `pyproject.toml`, so projects that already use that format require no structural changes. `uv` generates a `uv.lock` file (deterministic, cross-platform) that replaces `poetry.lock` or `pip freeze` outputs. Committing this file guarantees reproducible environments across machines and CI runners.

Common commands map naturally from existing tools:

```bash
uv sync            # install all dependencies from lockfile
uv add httpx       # add a package and update lockfile
uv run pytest      # run a command inside the managed venv
uv run python app/main.py
```

`uv run` is particularly ergonomic: it activates the virtual environment implicitly without requiring `source .venv/bin/activate`. It also reads the `[project.scripts]` table from `pyproject.toml`, so custom entry points work out of the box. Unlike Poetry, `uv` does not manage publishing to PyPI, keeping its scope intentionally narrow and its maintenance surface small.
