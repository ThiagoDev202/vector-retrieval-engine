---
title: "Poetry vs uv: dependency management"
source: autoral
language: en
---

# Poetry vs uv: dependency management

Both Poetry and uv manage Python dependencies, generate lockfiles, and isolate virtual environments. They differ significantly in speed, standards compliance, and feature scope.

**Resolver speed** is where uv wins decisively. uv's resolver is written in Rust and resolves a typical project in under a second on a warm cache. Poetry's Python-based resolver can take 30–120 seconds on projects with many transitive dependencies and complex version constraints. On a cold cache (CI first run), uv installs packages 10–100x faster than Poetry according to independent benchmarks.

**Lockfile format**: Poetry uses `poetry.lock`, a proprietary format. uv uses `uv.lock`, which is also proprietary but is designed alongside PEP 621 `pyproject.toml` — meaning the project metadata lives in the standard `[project]` table, not a `[tool.poetry]` section. This makes uv projects portable to other PEP 621-compliant tools.

**Workspace support**: uv supports monorepos with multiple packages via `[tool.uv.workspace]`. Poetry's workspace feature (groups) is narrower and does not map directly to PEP 517 editable installs across packages.

```toml
# uv workspace root
[tool.uv.workspace]
members = ["packages/*"]
```

**Verdict for new projects**: use uv. It is faster, standards-aligned, and actively developed with Astral's backing. Poetry remains a solid choice for existing projects where migration cost outweighs the benefits, but there is no strong reason to start a new project on Poetry in 2024+.
