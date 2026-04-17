"""Testes unitários para os embedders."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.core.exceptions import EmbeddingError
from app.search.embedder import FakeEmbedder, SentenceTransformerEmbedder


async def test_fake_embedder_empty_returns_zero_rows() -> None:
    """Embedding de lista vazia tem shape (0, dimension)."""
    embedder = FakeEmbedder()
    vectors = await embedder.embed([])
    assert vectors.shape == (0, 384)
    assert vectors.dtype == np.float32


async def test_fake_embedder_single_text_is_unit_norm() -> None:
    """Embedding de texto único retorna vetor float32 com norma ~1.0."""
    embedder = FakeEmbedder()
    vectors = await embedder.embed(["texto"])
    assert vectors.shape == (1, 384)
    assert vectors.dtype == np.float32
    assert float(np.linalg.norm(vectors[0])) == pytest.approx(1.0, abs=1e-5)


async def test_fake_embedder_is_deterministic() -> None:
    """Mesmo texto gera vetor idêntico independente da posição."""
    embedder = FakeEmbedder()
    vectors = await embedder.embed(["a", "b", "a"])
    assert vectors.shape == (3, 384)
    np.testing.assert_array_equal(vectors[0], vectors[2])
    assert not np.array_equal(vectors[0], vectors[1])


def test_fake_embedder_tokenize_detokenize_round_trip() -> None:
    """tokenize seguido de detokenize preserva o texto por palavras."""
    embedder = FakeEmbedder()
    tokens = embedder.tokenize("foo bar")
    assert embedder.detokenize(tokens) == "foo bar"


def test_sentence_transformer_load_initializes_model() -> None:
    """load() instancia SentenceTransformer e descobre dimensão."""
    with patch("sentence_transformers.SentenceTransformer") as mock_cls:
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 768
        mock_cls.return_value = mock_model

        embedder = SentenceTransformerEmbedder("algum-modelo")
        assert embedder.model is None
        assert embedder.dimension == 0

        embedder.load()

        mock_cls.assert_called_once_with("algum-modelo", device="cpu")
        assert embedder.dimension == 768
        assert embedder.model is mock_model

        # segunda chamada é no-op
        embedder.load()
        mock_cls.assert_called_once()


def test_sentence_transformer_tokenize_requires_load() -> None:
    """tokenize antes de load falha com EmbeddingError."""
    embedder = SentenceTransformerEmbedder("algum-modelo")
    with pytest.raises(EmbeddingError):
        embedder.tokenize("abc")


async def test_sentence_transformer_embed_requires_load() -> None:
    """embed antes de load falha com EmbeddingError."""
    embedder = SentenceTransformerEmbedder("algum-modelo")
    with pytest.raises(EmbeddingError):
        await embedder.embed(["abc"])


def test_sentence_transformer_tokenize_detokenize_delegates_to_tokenizer() -> None:
    """tokenize e detokenize usam o tokenizer do modelo carregado."""
    with patch("sentence_transformers.SentenceTransformer") as mock_cls:
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 16
        mock_model.tokenizer.encode.return_value = [7, 8, 9]
        mock_model.tokenizer.decode.return_value = "olá mundo"
        mock_cls.return_value = mock_model

        embedder = SentenceTransformerEmbedder("algum-modelo")
        embedder.load()

        assert embedder.tokenize("olá mundo") == [7, 8, 9]
        mock_model.tokenizer.encode.assert_called_once_with("olá mundo", add_special_tokens=False)

        assert embedder.detokenize([7, 8, 9]) == "olá mundo"
        mock_model.tokenizer.decode.assert_called_once_with([7, 8, 9], skip_special_tokens=True)


async def test_sentence_transformer_embed_empty_returns_zero_rows() -> None:
    """embed([]) devolve shape (0, dimension) sem chamar o modelo."""
    with patch("sentence_transformers.SentenceTransformer") as mock_cls:
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 32
        mock_cls.return_value = mock_model

        embedder = SentenceTransformerEmbedder("algum-modelo")
        embedder.load()

        vectors = await embedder.embed([])
        assert vectors.shape == (0, 32)
        mock_model.encode.assert_not_called()


async def test_sentence_transformer_embed_returns_float32_array() -> None:
    """embed converte a saída do modelo para float32."""
    with patch("sentence_transformers.SentenceTransformer") as mock_cls:
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 4
        mock_model.encode.return_value = np.array(
            [[0.1, 0.2, 0.3, 0.4], [0.5, 0.6, 0.7, 0.8]], dtype=np.float64
        )
        mock_cls.return_value = mock_model

        embedder = SentenceTransformerEmbedder("algum-modelo")
        embedder.load()

        vectors = await embedder.embed(["a", "b"])
        assert vectors.shape == (2, 4)
        assert vectors.dtype == np.float32
        mock_model.encode.assert_called_once_with(
            ["a", "b"],
            normalize_embeddings=True,
            convert_to_numpy=True,
        )


async def test_sentence_transformer_embed_propagates_embedding_error() -> None:
    """Falha do backend é re-levantada como EmbeddingError."""
    with patch("sentence_transformers.SentenceTransformer") as mock_cls:
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 4
        mock_model.encode.side_effect = RuntimeError("boom")
        mock_cls.return_value = mock_model

        embedder = SentenceTransformerEmbedder("algum-modelo")
        embedder.load()

        with pytest.raises(EmbeddingError):
            await embedder.embed(["a"])


async def test_sentence_transformer_embed_raises_on_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Timeout do backend é re-levantado como EmbeddingError com mensagem 'timeout'."""
    import time

    from app.search import embedder as embedder_module

    fake_model = MagicMock()
    fake_model.get_sentence_embedding_dimension.return_value = 384
    # encode dorme mais que o timeout configurado (0.05s)
    fake_model.encode.side_effect = lambda *a, **kw: (time.sleep(0.5), None)[1]  # type: ignore[misc]

    with patch("sentence_transformers.SentenceTransformer", return_value=fake_model):
        emb = SentenceTransformerEmbedder("fake-model")
        emb.load()

    # Timeout muito curto para o teste ser rápido — aplicado após o load()
    monkeypatch.setattr(embedder_module, "_EMBED_TIMEOUT_SECONDS", 0.05)

    with pytest.raises(EmbeddingError, match="timeout"):
        await emb.embed(["algum texto"])
