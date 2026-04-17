"""Estratégia de chunking por tokens com janela deslizante."""

from collections.abc import Callable

Tokenizer = Callable[[str], list[int]]
Detokenizer = Callable[[list[int]], str]


def split_text(
    text: str,
    chunk_size: int,
    overlap: int,
    tokenize: Tokenizer,
    detokenize: Detokenizer,
) -> list[str]:
    """Divide texto em chunks de até ``chunk_size`` tokens com ``overlap`` de sobreposição."""
    if chunk_size <= 0:
        raise ValueError("chunk_size deve ser maior que zero")
    if overlap < 0:
        raise ValueError("overlap não pode ser negativo")
    if overlap >= chunk_size:
        raise ValueError("overlap deve ser menor que chunk_size")

    if not text or not text.strip():
        return []

    trimmed = text.strip()
    tokens = tokenize(trimmed)

    if len(tokens) <= chunk_size:
        return [trimmed]

    chunks: list[str] = []
    step = chunk_size - overlap
    start = 0
    total = len(tokens)
    while start < total:
        end = start + chunk_size
        chunk_tokens = tokens[start:end]
        if not chunk_tokens:
            break
        chunks.append(detokenize(chunk_tokens))
        if end >= total:
            break
        start += step
    return chunks
