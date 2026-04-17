"""Abstrações e implementações de geradores de embeddings."""

from __future__ import annotations

import asyncio
import hashlib
from typing import Protocol, runtime_checkable

import numpy as np
from numpy.typing import NDArray

from app.core.exceptions import EmbeddingError

_EMBED_TIMEOUT_SECONDS: float = 30.0


@runtime_checkable
class Embedder(Protocol):
    """Interface comum para geradores de embeddings."""

    dimension: int

    def load(self) -> None:
        """Carrega recursos pesados (modelo/tokenizer). Idempotente."""
        ...

    def tokenize(self, text: str) -> list[int]:
        """Converte texto em lista de IDs de token."""
        ...

    def detokenize(self, tokens: list[int]) -> str:
        """Reconstrói texto a partir de uma lista de IDs de token."""
        ...

    async def embed(self, texts: list[str]) -> NDArray[np.float32]:
        """Gera embeddings normalizados para a lista de textos."""
        ...


class SentenceTransformerEmbedder:
    """Embedder baseado em sentence-transformers carregado sob demanda."""

    def __init__(self, model_name: str, *, device: str = "cpu") -> None:
        self.model_name = model_name
        self.device = device
        self.dimension: int = 0
        self.model: object | None = None

    def load(self) -> None:
        """Carrega o modelo sentence-transformers se ainda não estiver carregado."""
        if self.model is not None:
            return
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(self.model_name, device=self.device)
        dim = model.get_sentence_embedding_dimension()
        if not isinstance(dim, int) or dim <= 0:
            raise EmbeddingError("dimensão do modelo de embeddings inválida")
        self.model = model
        self.dimension = dim

    def _require_model(self) -> object:
        """Garante que o modelo foi carregado antes do uso."""
        if self.model is None:
            raise EmbeddingError("modelo de embeddings não carregado; chame load() antes")
        return self.model

    def tokenize(self, text: str) -> list[int]:
        """Tokeniza texto usando o tokenizer interno do modelo."""
        model = self._require_model()
        tokenizer = model.tokenizer  # type: ignore[attr-defined]
        ids = tokenizer.encode(text, add_special_tokens=False)
        return list(ids)

    def detokenize(self, tokens: list[int]) -> str:
        """Reconstrói texto a partir dos IDs do tokenizer interno."""
        model = self._require_model()
        tokenizer = model.tokenizer  # type: ignore[attr-defined]
        decoded = tokenizer.decode(tokens, skip_special_tokens=True)
        return str(decoded)

    async def embed(self, texts: list[str]) -> NDArray[np.float32]:
        """Gera embeddings em thread auxiliar para não bloquear o event loop."""
        model = self._require_model()
        if not texts:
            return np.zeros((0, self.dimension), dtype=np.float32)

        def _encode() -> NDArray[np.float32]:
            raw = model.encode(  # type: ignore[attr-defined]
                texts,
                normalize_embeddings=True,
                convert_to_numpy=True,
            )
            array = np.asarray(raw)
            if array.dtype != np.float32:
                array = array.astype(np.float32, copy=False)
            return array

        try:
            async with asyncio.timeout(_EMBED_TIMEOUT_SECONDS):
                return await asyncio.to_thread(_encode)
        except TimeoutError as exc:
            raise EmbeddingError("timeout ao gerar embedding") from exc
        except Exception as exc:  # noqa: BLE001 - queremos encapsular qualquer erro do backend
            raise EmbeddingError("falha ao gerar embedding") from exc


class FakeEmbedder:
    """Embedder determinístico usado em testes — sem dependência de modelo real."""

    def __init__(self, dimension: int = 384) -> None:
        self.dimension = dimension
        self._vocab: list[str] = []
        self._vocab_index: dict[str, int] = {}

    def _word_id(self, word: str) -> int:
        """Retorna (ou cria) o ID inteiro associado à palavra."""
        if word not in self._vocab_index:
            self._vocab_index[word] = len(self._vocab)
            self._vocab.append(word)
        return self._vocab_index[word]

    def load(self) -> None:
        """No-op: o embedder falso não tem recursos pesados."""
        return

    def tokenize(self, text: str) -> list[int]:
        """Tokeniza por whitespace mantendo vocabulário estável."""
        return [self._word_id(w) for w in text.split()]

    def detokenize(self, tokens: list[int]) -> str:
        """Reconstrói texto juntando as palavras do vocabulário por espaço."""
        return " ".join(self._vocab[t] for t in tokens)

    async def embed(self, texts: list[str]) -> NDArray[np.float32]:
        """Gera vetores determinísticos L2-normalizados a partir do hash do texto."""
        if not texts:
            return np.zeros((0, self.dimension), dtype=np.float32)

        out = np.zeros((len(texts), self.dimension), dtype=np.float32)
        for i, text in enumerate(texts):
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
            seed = int(digest, 16)
            rng = np.random.default_rng(seed)
            vec = rng.standard_normal(self.dimension).astype(np.float32)
            norm = float(np.linalg.norm(vec))
            vec /= norm + 1e-12
            out[i] = vec
        return out
