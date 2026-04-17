"""Lógica de negócio do módulo de busca semântica."""

from uuid import uuid4

from app.search.chunking import split_text
from app.search.embedder import Embedder
from app.search.schemas import (
    ChunkOut,
    DocumentDetail,
    DocumentIn,
    DocumentOut,
    HealthResponse,
    SearchHitOut,
    SearchQuery,
    SearchResponse,
    StatsResponse,
)
from app.search.store import FaissVectorStore


class SearchService:
    """Orquestra indexação, busca e gerenciamento de documentos."""

    def __init__(
        self,
        embedder: Embedder,
        store: FaissVectorStore,
        *,
        chunk_size: int,
        chunk_overlap: int,
        default_top_k: int,
        embedding_model_name: str,
    ) -> None:
        self._embedder = embedder
        self._store = store
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._default_top_k = default_top_k
        self._embedding_model_name = embedding_model_name

    async def add_document(self, payload: DocumentIn) -> DocumentOut:
        """Indexa um documento, particionando em chunks e gerando embeddings."""
        doc_id = payload.id or uuid4().hex
        chunks = split_text(
            payload.content,
            self._chunk_size,
            self._chunk_overlap,
            self._embedder.tokenize,
            self._embedder.detokenize,
        )
        if len(chunks) == 0:
            raise ValueError("conteúdo vazio após tokenização")
        vectors = await self._embedder.embed(chunks)
        await self._store.add(doc_id, chunks, vectors, payload.metadata or None)
        await self._store.save()
        return DocumentOut(
            document_id=doc_id,
            chunk_count=len(chunks),
            dimension=self._embedder.dimension,
        )

    async def search(self, query: SearchQuery) -> SearchResponse:
        """Executa busca semântica retornando os hits mais relevantes."""
        top_k = query.top_k or self._default_top_k
        vectors = await self._embedder.embed([query.query])
        hits = await self._store.search(vectors[0], top_k)
        hits_out = [
            SearchHitOut(
                document_id=h.document_id,
                chunk=h.chunk,
                chunk_idx=h.chunk_idx,
                score=h.score,
                metadata=h.metadata,
            )
            for h in hits
        ]
        return SearchResponse(query=query.query, hits=hits_out)

    async def get_document(self, document_id: str) -> DocumentDetail:
        """Retorna todos os chunks de um documento pelo seu ID."""
        records = await self._store.get_document(document_id)
        chunks = [
            ChunkOut(
                chunk_idx=r.chunk_idx,
                text=r.chunk_text,
                metadata=dict(r.metadata),
            )
            for r in records
        ]
        metadata = dict(records[0].metadata) if records else {}
        return DocumentDetail(document_id=document_id, chunks=chunks, metadata=metadata)

    async def delete_document(self, document_id: str) -> None:
        """Remove um documento e todos os seus chunks do índice."""
        await self._store.delete(document_id)
        await self._store.save()

    def stats(self) -> StatsResponse:
        """Retorna estatísticas agregadas do índice."""
        raw = self._store.stats()
        return StatsResponse(
            document_count=int(raw["document_count"]),
            chunk_count=int(raw["chunk_count"]),
            embedding_model=self._embedding_model_name,
            dimension=int(raw["dimension"]),
        )

    def health(self) -> HealthResponse:
        """Retorna status de saúde do serviço."""
        return HealthResponse(status="ok", index_ready=True)
