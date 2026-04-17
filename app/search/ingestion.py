"""Ingestão do corpus bundled em Markdown."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from app.core.exceptions import DocumentNotFoundError
from app.search.schemas import DocumentIn

if TYPE_CHECKING:
    from app.search.service import SearchService


logger = logging.getLogger(__name__)

_FRONT_MATTER_RE = re.compile(r"\A---\s*\n(?P<meta>.*?)\n---\s*\n?(?P<body>.*)\Z", re.DOTALL)


def _parse_front_matter(raw: str) -> tuple[dict[str, str], str]:
    """Extrai front-matter YAML simples (chave: valor por linha) e retorna (metadata, corpo).

    Não suporta YAML aninhado nem listas — intencionalmente restrito para evitar dependência
    externa. Chaves e valores são trimados; linhas em branco dentro do front-matter são ignoradas.
    """
    match = _FRONT_MATTER_RE.match(raw)
    if match is None:
        return {}, raw.strip()

    metadata: dict[str, str] = {}
    for line in match.group("meta").splitlines():
        stripped = line.strip()
        if not stripped or ":" not in stripped:
            continue
        key, _, value = stripped.partition(":")
        metadata[key.strip()] = value.strip()
    return metadata, match.group("body").strip()


async def load_corpus(corpus_dir: Path, service: SearchService) -> int:
    """Indexa todos os `.md` de `corpus_dir` ainda não presentes no índice.

    Retorna a contagem de documentos efetivamente adicionados nesta chamada.
    Documentos cujo `document_id` (stem do arquivo) já existem no índice são pulados.
    """
    if not corpus_dir.exists():
        logger.info("diretório de corpus inexistente: %s", corpus_dir)
        return 0

    added = 0
    for md_path in sorted(corpus_dir.glob("*.md")):
        doc_id = md_path.stem
        try:
            await service.get_document(doc_id)
            continue
        except DocumentNotFoundError:
            pass

        raw = md_path.read_text(encoding="utf-8")
        front_matter, body = _parse_front_matter(raw)
        if not body:
            logger.warning("arquivo vazio ignorado: %s", md_path)
            continue

        metadata: dict[str, Any] = dict(front_matter)
        metadata.setdefault("filename", md_path.name)

        await service.add_document(
            DocumentIn(id=doc_id, content=body, metadata=metadata),
        )
        added += 1

    logger.info("corpus carregado: %d documentos novos em %s", added, corpus_dir)
    return added
