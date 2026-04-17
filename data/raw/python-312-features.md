---
title: Python 3.12 highlights
source: autoral
language: en
---

# Python 3.12 highlights

Python 3.12 (released October 2023) ships several changes that directly affect how modern Python code is written and how fast it runs.

**PEP 695 — Type parameter syntax** introduces a compact way to declare generic classes and functions without importing `TypeVar` explicitly:

```python
# Before (3.11)
from typing import TypeVar
T = TypeVar("T")
def first(items: list[T]) -> T: ...

# After (3.12)
def first[T](items: list[T]) -> T: ...
```

**Improved f-strings** lift several parser restrictions: you can now reuse the same quote character inside the expression, nest f-strings arbitrarily, and embed multi-line expressions — all without workarounds.

**`@override` from `typing`** lets type checkers verify that a method in a subclass actually overrides a method from the parent. If the parent method is renamed or removed, mypy raises an error at the call site instead of silently allowing a stale override.

**Faster comprehensions** result from PEP 709, which inlines list, dict, and set comprehensions into the enclosing frame rather than creating a new frame for each iteration. Benchmarks show 2x speedups for simple comprehensions in tight loops.

**Isolated subinterpreters** (PEP 684) give each subinterpreter its own GIL, enabling true multi-core parallelism within a single process. As of 3.12 the feature is marked experimental; the higher-level `interpreters` module API stabilizes in 3.13. Practical adoption is still limited to specialized use cases.
