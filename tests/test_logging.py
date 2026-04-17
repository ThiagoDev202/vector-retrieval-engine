"""Testes para o módulo de logging estruturado com sanitização contra log injection."""

import json
import logging

import pytest

from app.core.logging import JsonFormatter, _sanitize, configure_logging


def _format(record_kwargs: dict) -> dict:  # type: ignore[type-arg]
    """Cria um LogRecord a partir de kwargs e retorna o payload JSON decodificado."""
    record = logging.makeLogRecord(record_kwargs)
    out = JsonFormatter().format(record)
    return json.loads(out)  # type: ignore[no-any-return]


class TestSanitizeStripsNewlinesAndControlChars:
    def test_newlines_and_carriage_returns_removed_from_message(self) -> None:
        msg = 'linha 1\nINJECTED: {"level":"CRITICAL"}\rmais'
        payload = _format({"msg": msg, "level": logging.INFO, "levelname": "INFO"})
        raw_json = json.dumps(payload, ensure_ascii=False)
        # Não deve haver newline ou CR literais dentro do valor message
        assert "\n" not in payload["message"]  # type: ignore[operator]
        assert "\r" not in payload["message"]  # type: ignore[operator]
        # O JSON serializado do payload também não deve conter literais
        assert "\n" not in raw_json
        assert "\r" not in raw_json

    def test_message_content_concatenated_without_controls(self) -> None:
        msg = 'linha 1\nINJECTED: {"level":"CRITICAL"}\rmais'
        payload = _format({"msg": msg, "level": logging.INFO, "levelname": "INFO"})
        assert payload["message"] == 'linha 1INJECTED: {"level":"CRITICAL"}mais'

    def test_null_byte_stripped(self) -> None:
        payload = _format({"msg": "abc\x00def", "level": logging.INFO, "levelname": "INFO"})
        assert "\x00" not in payload["message"]  # type: ignore[operator]
        assert payload["message"] == "abcdef"

    def test_other_control_chars_stripped(self) -> None:
        payload = _format({"msg": "a\x01\x02\x1fb", "level": logging.INFO, "levelname": "INFO"})
        assert payload["message"] == "ab"

    def test_tab_preserved(self) -> None:
        payload = _format({"msg": "col1\tcol2", "level": logging.INFO, "levelname": "INFO"})
        assert payload["message"] == "col1\tcol2"


class TestSanitizePreservesUnicode:
    def test_unicode_message_intact(self) -> None:
        msg = "café ☕ 中文"
        payload = _format({"msg": msg, "level": logging.INFO, "levelname": "INFO"})
        assert payload["message"] == msg

    def test_unicode_in_extra(self) -> None:
        record = logging.makeLogRecord({"msg": "ok", "level": logging.INFO, "levelname": "INFO"})
        record.__dict__["idioma"] = "português"
        out = JsonFormatter().format(record)
        loaded = json.loads(out)
        assert loaded["extra"]["idioma"] == "português"


class TestSanitizeTruncatesLongList:
    def test_list_over_50_items_truncated(self) -> None:
        big_list = list(range(200))
        result = _sanitize({"big": big_list})
        assert isinstance(result, dict)
        sanitized_list = result["big"]
        assert isinstance(sanitized_list, list)
        # 50 items + 1 marker
        assert len(sanitized_list) == 51
        assert sanitized_list[-1] == "...(150 items omitted)"

    def test_list_under_limit_not_truncated(self) -> None:
        small_list = list(range(10))
        result = _sanitize(small_list)
        assert isinstance(result, list)
        assert len(result) == 10

    def test_list_at_limit_not_truncated(self) -> None:
        exact_list = list(range(50))
        result = _sanitize(exact_list)
        assert isinstance(result, list)
        assert len(result) == 50

    def test_extra_with_big_list_via_formatter(self) -> None:
        record = logging.makeLogRecord({"msg": "x", "level": logging.INFO, "levelname": "INFO"})
        record.__dict__["big"] = list(range(200))
        out = JsonFormatter().format(record)
        loaded = json.loads(out)
        big_val = loaded["extra"]["big"]
        assert isinstance(big_val, list)
        assert len(big_val) == 51
        assert big_val[-1] == "...(150 items omitted)"


class TestSanitizeLimitsRecursionDepth:
    def test_depth_4_becomes_depth_limit(self) -> None:
        # depth 0 → dict a
        # depth 1 → dict b
        # depth 2 → dict c
        # depth 3 → dict d
        # depth 4 → "deep" — excede _MAX_RECURSION_DEPTH=3, vira "<depth limit>"
        nested = {"a": {"b": {"c": {"d": "deep"}}}}
        result = _sanitize(nested)
        assert isinstance(result, dict)
        a = result["a"]
        assert isinstance(a, dict)
        b = a["b"]
        assert isinstance(b, dict)
        c = b["c"]
        assert isinstance(c, dict)
        assert c["d"] == "<depth limit>"

    def test_depth_3_value_preserved(self) -> None:
        # depth 0 → a, depth 1 → b, depth 2 → c, depth 3 → "ok" (igual ao limite, não excede)
        nested = {"a": {"b": {"c": "ok"}}}
        result = _sanitize(nested)
        assert isinstance(result, dict)
        assert result["a"]["b"]["c"] == "ok"  # type: ignore[index]


class TestSanitizeHandlesNonSerializableObject:
    def test_custom_object_becomes_repr(self) -> None:
        class X:
            pass

        x = X()
        result = _sanitize(x)
        assert isinstance(result, str)
        assert len(result) <= 200
        # repr de instância contém o nome da classe
        assert "X" in result

    def test_repr_truncated_to_200_chars(self) -> None:
        class BigRepr:
            def __repr__(self) -> str:
                return "x" * 500

        result = _sanitize(BigRepr())
        assert isinstance(result, str)
        assert len(result) == 200

    def test_bytes_decoded_and_sanitized(self) -> None:
        result = _sanitize(b"abc\x0adef")
        assert isinstance(result, str)
        assert "\n" not in result
        assert result == "abcdef"


class TestSanitizePrimitives:
    def test_none_preserved(self) -> None:
        assert _sanitize(None) is None

    def test_bool_preserved(self) -> None:
        assert _sanitize(True) is True
        assert _sanitize(False) is False

    def test_int_preserved(self) -> None:
        assert _sanitize(42) == 42

    def test_float_preserved(self) -> None:
        assert _sanitize(3.14) == pytest.approx(3.14)


class TestConfigureLogging:
    def test_installs_json_formatter(self) -> None:
        configure_logging("DEBUG")
        root = logging.getLogger()
        assert len(root.handlers) >= 1
        formatter = root.handlers[0].formatter
        assert isinstance(formatter, JsonFormatter)

    def test_sets_correct_level(self) -> None:
        configure_logging("DEBUG")
        root = logging.getLogger()
        assert root.level == logging.DEBUG

    def test_info_level(self) -> None:
        configure_logging("INFO")
        root = logging.getLogger()
        assert root.level == logging.INFO

    def test_output_is_valid_json(self) -> None:
        configure_logging("DEBUG")
        payload = _format({"msg": "hello", "level": logging.INFO, "levelname": "INFO"})
        assert payload["message"] == "hello"
        assert payload["level"] == "INFO"
        assert "timestamp" in payload
        assert "logger" in payload
