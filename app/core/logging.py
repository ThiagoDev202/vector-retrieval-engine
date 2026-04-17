"""Configuração de logging estruturado em formato JSON."""

import json
import logging
import re
from datetime import UTC, datetime

_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0A-\x1F]")  # todos os controles exceto TAB

_MAX_RECURSION_DEPTH = 3
_MAX_SEQUENCE_LENGTH = 50
_MAX_REPR_LENGTH = 200


def _sanitize(value: object, depth: int = 0) -> object:
    """Remove control chars e garante serializabilidade do valor."""
    if depth > _MAX_RECURSION_DEPTH:
        return "<depth limit>"
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        return _CONTROL_CHARS_RE.sub("", value)
    if isinstance(value, bytes):
        decoded = value.decode("latin-1", errors="replace")
        return _CONTROL_CHARS_RE.sub("", decoded)
    if isinstance(value, dict):
        return {str(k): _sanitize(v, depth + 1) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        items = list(value)
        if len(items) > _MAX_SEQUENCE_LENGTH:
            sanitized: list[object] = [
                _sanitize(it, depth + 1) for it in items[:_MAX_SEQUENCE_LENGTH]
            ]
            sanitized.append(f"...({len(items) - _MAX_SEQUENCE_LENGTH} items omitted)")
            return sanitized
        return [_sanitize(it, depth + 1) for it in items]
    return repr(value)[:_MAX_REPR_LENGTH]


class JsonFormatter(logging.Formatter):
    """Formata log records como JSON de uma linha com campos padronizados."""

    def format(self, record: logging.LogRecord) -> str:
        """Retorna registro de log serializado como JSON."""
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": _sanitize(record.getMessage()),
        }

        extra: dict[str, object] = {
            key: _sanitize(value)
            for key, value in record.__dict__.items()
            if key
            not in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "taskName",
                "message",
            }
        }

        if extra:
            payload["extra"] = extra

        if record.exc_info:
            payload["exc_info"] = _sanitize(self.formatException(record.exc_info))

        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_logging(level: str = "INFO") -> None:
    """Configura o root logger para emitir JSON estruturado."""
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
