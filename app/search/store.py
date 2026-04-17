"""Vector store baseado em FAISS com persistência em disco."""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import faiss
import numpy as np
from numpy.typing import NDArray

from app.core.exceptions import DocumentNotFoundError, IndexUnavailableError

_INDEX_FILENAME = "faiss.index"
_METADATA_FILENAME = "metadata.json"
_VECTORS_FILENAME = "vectors.npy"


@dataclass(slots=True)
class SearchHit:
    """Resultado de uma busca vetorial."""

    document_id: str
    chunk: str
    chunk_idx: int
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class ChunkRecord:
    """Registro interno: um chunk indexado."""

    document_id: str
    chunk_idx: int
    chunk_text: str
    metadata: dict[str, Any] = field(default_factory=dict)


class FaissVectorStore:
    """Armazena vetores normalizados em um ``IndexFlatIP`` com persistência atômica."""

    def __init__(self, index_dir: Path, dimension: int) -> None:
        self._index_dir = index_dir
        self._dimension = dimension
        self._index = faiss.IndexFlatIP(dimension)
        self._records: list[ChunkRecord] = []
        self._doc_positions: dict[str, list[int]] = {}
        self._vectors: NDArray[np.float32] = np.zeros((0, dimension), dtype=np.float32)
        self._lock = asyncio.Lock()

    async def add(
        self,
        document_id: str,
        chunks: list[str],
        vectors: NDArray[np.float32],
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Adiciona os chunks de um documento ao índice, retornando quantos foram inseridos."""
        if len(chunks) == 0:
            if vectors.shape != (0, self._dimension) or vectors.dtype != np.float32:
                raise ValueError("shape ou dtype inválido")
            return 0

        expected_shape = (len(chunks), self._dimension)
        if vectors.shape != expected_shape or vectors.dtype != np.float32:
            raise ValueError("shape ou dtype inválido")

        async with self._lock:
            if document_id in self._doc_positions:
                raise ValueError(f"documento '{document_id}' já indexado")

            start = len(self._records)
            positions = list(range(start, start + len(chunks)))

            self._index.add(vectors)
            self._vectors = np.concatenate([self._vectors, vectors], axis=0)

            chunk_metadata = dict(metadata) if metadata else {}
            new_records = [
                ChunkRecord(
                    document_id=document_id,
                    chunk_idx=i,
                    chunk_text=chunk,
                    metadata=chunk_metadata,
                )
                for i, chunk in enumerate(chunks)
            ]
            self._records.extend(new_records)
            self._doc_positions[document_id] = positions

            return len(chunks)

    async def search(self, query_vector: NDArray[np.float32], top_k: int) -> list[SearchHit]:
        """Busca os ``top_k`` vizinhos mais próximos do ``query_vector`` no índice."""
        if top_k <= 0:
            raise ValueError("top_k deve ser maior que zero")

        if query_vector.dtype != np.float32:
            raise ValueError("shape ou dtype inválido")

        if query_vector.ndim == 1:
            if query_vector.shape != (self._dimension,):
                raise ValueError("shape ou dtype inválido")
            query_2d = query_vector.reshape(1, self._dimension)
        elif query_vector.ndim == 2:
            if query_vector.shape != (1, self._dimension):
                raise ValueError("shape ou dtype inválido")
            query_2d = query_vector
        else:
            raise ValueError("shape ou dtype inválido")

        ntotal = int(self._index.ntotal)
        if ntotal == 0:
            return []

        effective_k = min(top_k, ntotal)
        scores, ids = await asyncio.to_thread(self._index.search, query_2d, effective_k)

        hits: list[SearchHit] = []
        for rank in range(effective_k):
            faiss_id = int(ids[0][rank])
            if faiss_id < 0:
                continue
            record = self._records[faiss_id]
            hits.append(
                SearchHit(
                    document_id=record.document_id,
                    chunk=record.chunk_text,
                    chunk_idx=record.chunk_idx,
                    score=float(scores[0][rank]),
                    metadata=dict(record.metadata),
                )
            )
        return hits

    async def get_document(self, document_id: str) -> list[ChunkRecord]:
        """Retorna os chunks de um documento ordenados por ``chunk_idx``."""
        positions = self._doc_positions.get(document_id)
        if positions is None:
            raise DocumentNotFoundError(document_id)
        records = [self._records[pos] for pos in positions]
        return sorted(records, key=lambda r: r.chunk_idx)

    async def delete(self, document_id: str) -> int:
        """Remove todos os chunks de um documento e reconstrói o índice."""
        async with self._lock:
            positions = self._doc_positions.get(document_id)
            if positions is None:
                raise DocumentNotFoundError(document_id)

            removed = len(positions)
            to_remove = set(positions)

            keep_mask = np.ones(len(self._records), dtype=bool)
            for pos in positions:
                keep_mask[pos] = False

            kept_records = [r for i, r in enumerate(self._records) if i not in to_remove]
            kept_vectors = self._vectors[keep_mask]

            new_index = faiss.IndexFlatIP(self._dimension)
            if kept_vectors.shape[0] > 0:
                new_index.add(kept_vectors)

            new_doc_positions: dict[str, list[int]] = {}
            for new_pos, record in enumerate(kept_records):
                new_doc_positions.setdefault(record.document_id, []).append(new_pos)

            self._index = new_index
            self._records = kept_records
            self._vectors = kept_vectors
            self._doc_positions = new_doc_positions

            return removed

    async def save(self) -> None:
        """Serializa índice, vetores e metadados de forma atômica em ``index_dir``."""
        async with self._lock:
            await asyncio.to_thread(self._save_sync)

    def _save_sync(self) -> None:
        """Persistência síncrona executada em thread auxiliar."""
        self._index_dir.mkdir(parents=True, exist_ok=True)

        index_path = self._index_dir / _INDEX_FILENAME
        metadata_path = self._index_dir / _METADATA_FILENAME
        vectors_path = self._index_dir / _VECTORS_FILENAME

        index_tmp = self._index_dir / f"{_INDEX_FILENAME}.tmp"
        metadata_tmp = self._index_dir / f"{_METADATA_FILENAME}.tmp"
        vectors_tmp = self._index_dir / f"{_VECTORS_FILENAME}.tmp.npy"

        faiss.write_index(self._index, str(index_tmp))

        payload: dict[str, Any] = {
            "dimension": self._dimension,
            "records": [asdict(record) for record in self._records],
            "doc_positions": self._doc_positions,
        }
        metadata_tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        # ``np.save`` preserva o nome quando o caminho já termina com ``.npy``.
        np.save(str(vectors_tmp), self._vectors)

        os.replace(index_tmp, index_path)
        os.replace(metadata_tmp, metadata_path)
        os.replace(vectors_tmp, vectors_path)

    async def load(self) -> bool:
        """Carrega índice persistido; retorna ``False`` se não houver dados."""
        async with self._lock:
            return await asyncio.to_thread(self._load_sync)

    def _load_sync(self) -> bool:
        """Carregamento síncrono executado em thread auxiliar."""
        index_path = self._index_dir / _INDEX_FILENAME
        metadata_path = self._index_dir / _METADATA_FILENAME
        vectors_path = self._index_dir / _VECTORS_FILENAME

        if not (index_path.exists() and metadata_path.exists() and vectors_path.exists()):
            return False

        try:
            raw = metadata_path.read_text(encoding="utf-8")
            payload = json.loads(raw)
            loaded_dim = int(payload["dimension"])
            if loaded_dim != self._dimension:
                raise IndexUnavailableError("dimensão do índice não bate com configuração")

            records = [ChunkRecord(**record) for record in payload["records"]]
            doc_positions = {
                str(doc_id): [int(pos) for pos in positions]
                for doc_id, positions in payload["doc_positions"].items()
            }
            index = faiss.read_index(str(index_path))
            vectors = np.load(vectors_path)
            if vectors.dtype != np.float32:
                vectors = vectors.astype(np.float32, copy=False)
        except IndexUnavailableError:
            raise
        except Exception as exc:
            raise IndexUnavailableError("falha ao carregar índice") from exc

        self._index = index
        self._records = records
        self._doc_positions = doc_positions
        self._vectors = vectors
        return True

    def stats(self) -> dict[str, int | str]:
        """Retorna contagens agregadas do índice atual."""
        return {
            "document_count": len(self._doc_positions),
            "chunk_count": int(self._index.ntotal),
            "dimension": self._dimension,
        }
