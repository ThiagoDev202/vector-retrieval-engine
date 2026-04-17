"""Testes de validação de limites em DTOs de entrada."""

import pytest
from pydantic import ValidationError

from app.search.schemas import DocumentIn, SearchQuery


class TestDocumentInContent:
    """Testa limites de tamanho do campo content."""

    def test_accepts_max_length(self) -> None:
        """Aceita content com exatamente 50_000 caracteres."""
        DocumentIn(content="x" * 50_000)

    def test_rejects_over_max(self) -> None:
        """Rejeita content com 50_001 caracteres."""
        with pytest.raises(ValidationError):
            DocumentIn(content="x" * 50_001)

    def test_rejects_empty_content(self) -> None:
        """Rejeita content vazio (min_length=1)."""
        with pytest.raises(ValidationError):
            DocumentIn(content="")


class TestDocumentInMetadata:
    """Testa validação de metadata em DocumentIn."""

    def test_accepts_empty_dict(self) -> None:
        """Aceita metadata vazio."""
        doc = DocumentIn(content="valid")
        assert doc.metadata == {}

    def test_accepts_exactly_20_keys(self) -> None:
        """Aceita metadata com exatamente 20 chaves."""
        metadata = {str(i): i for i in range(20)}
        DocumentIn(content="valid", metadata=metadata)

    def test_rejects_21_keys(self) -> None:
        """Rejeita metadata com 21 chaves."""
        metadata = {str(i): i for i in range(21)}
        with pytest.raises(ValidationError, match="metadata excede 20 chaves"):
            DocumentIn(content="valid", metadata=metadata)

    def test_rejects_nested_dict(self) -> None:
        """Rejeita valor aninhado do tipo dict."""
        with pytest.raises(ValidationError, match="valores primitivos"):
            DocumentIn(content="valid", metadata={"k": {"nested": "v"}})

    def test_rejects_list_value(self) -> None:
        """Rejeita valor do tipo list."""
        with pytest.raises(ValidationError, match="valores primitivos"):
            DocumentIn(content="valid", metadata={"k": [1, 2]})

    def test_accepts_primitive_mix(self) -> None:
        """Aceita mix de primitivos: str, int, float, bool, None."""
        DocumentIn(
            content="valid",
            metadata={
                "str_val": "hello",
                "int_val": 42,
                "float_val": 3.14,
                "bool_val": True,
                "none_val": None,
            },
        )

    def test_rejects_string_value_over_2000_chars(self) -> None:
        """Rejeita valor string com 2_001 caracteres."""
        with pytest.raises(ValidationError, match="valor de metadata excede 2000 caracteres"):
            DocumentIn(content="valid", metadata={"k": "x" * 2_001})

    def test_accepts_string_value_at_2000_chars(self) -> None:
        """Aceita valor string com exatamente 2_000 caracteres."""
        DocumentIn(content="valid", metadata={"k": "x" * 2_000})


class TestSearchQuery:
    """Testa limites de tamanho do campo query em SearchQuery."""

    def test_accepts_query_at_2000_chars(self) -> None:
        """Aceita query com exatamente 2_000 caracteres."""
        SearchQuery(query="q" * 2_000)

    def test_rejects_query_over_2000_chars(self) -> None:
        """Rejeita query com 2_001 caracteres."""
        with pytest.raises(ValidationError):
            SearchQuery(query="q" * 2_001)
