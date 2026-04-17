"""Hierarquia de erros de domínio da aplicação."""


class DomainError(Exception):
    """Erro base de domínio."""


class DocumentNotFoundError(DomainError):
    """Documento não existe no índice."""

    def __init__(self, document_id: str) -> None:
        self.document_id = document_id
        super().__init__(f"Documento não encontrado: {document_id}")


class EmbeddingError(DomainError):
    """Falha ao gerar embedding."""


class IndexUnavailableError(DomainError):
    """Índice FAISS não carregado ou corrompido."""
