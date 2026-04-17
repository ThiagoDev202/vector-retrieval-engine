---
title: Structured logging in Python without libs
source: autoral
language: en
---

# Structured logging in Python without libs

Structured logging emits log records as machine-readable JSON instead of free-form strings. This makes log aggregators (Elasticsearch, Loki, CloudWatch) able to filter and query by field without fragile regex parsing.

Python's standard `logging` module supports structured output through a custom `Formatter`. Subclassing `logging.Formatter` and overriding `format()` is all you need:

```python
import json
import logging
from datetime import datetime, timezone

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # merge any extra fields passed via logger.info("msg", extra={...})
        for key, value in record.__dict__.items():
            if key not in logging.LogRecord.__dict__ and not key.startswith("_"):
                payload[key] = value
        return json.dumps(payload, default=str)
```

Register the formatter on your handler:

```python
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logging.getLogger().addHandler(handler)
```

Callers add context via `extra`:

```python
logger.info("request handled", extra={"session_id": sid, "latency_ms": 42})
```

**ISO-8601 UTC timestamps** (`datetime.now(timezone.utc).isoformat()`) are preferred over `time.time()` floats because they are human-readable, unambiguous, and sort lexicographically. The `default=str` fallback in `json.dumps` prevents serialization errors for non-JSON-native types like `UUID` or `Decimal` without requiring explicit conversion at every call site.
