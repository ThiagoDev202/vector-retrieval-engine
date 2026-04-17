"""Testes de ingestão do corpus bundled."""

from pathlib import Path

from app.search.ingestion import _parse_front_matter, load_corpus
from app.search.service import SearchService


def test_parse_front_matter_with_metadata() -> None:
    raw = "---\ntitle: Um título\nsource: autoral\nlanguage: pt-br\n---\n\nCorpo do texto.\n"
    metadata, body = _parse_front_matter(raw)
    assert metadata == {"title": "Um título", "source": "autoral", "language": "pt-br"}
    assert body == "Corpo do texto."


def test_parse_front_matter_without_block() -> None:
    raw = "Sem front-matter, apenas texto."
    metadata, body = _parse_front_matter(raw)
    assert metadata == {}
    assert body == "Sem front-matter, apenas texto."


def test_parse_front_matter_ignores_blank_and_keyless_lines() -> None:
    raw = "---\ntitle: Abc\n\nlinha_sem_dois_pontos\nsource: autoral\n---\n\nCorpo.\n"
    metadata, _body = _parse_front_matter(raw)
    assert metadata == {"title": "Abc", "source": "autoral"}


async def test_load_corpus_indexes_markdown_files(
    tmp_path: Path, fake_service: SearchService
) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "alpha.md").write_text(
        "---\ntitle: Alpha\nlanguage: pt-br\n---\n\n"
        "Este é o conteúdo do documento alpha para teste de ingestão.\n",
        encoding="utf-8",
    )
    (corpus / "beta.md").write_text(
        "---\ntitle: Beta\nlanguage: en\n---\n\n"
        "This is the beta document content used during ingestion tests.\n",
        encoding="utf-8",
    )

    added = await load_corpus(corpus, fake_service)

    assert added == 2
    stats = fake_service.stats()
    assert stats.document_count == 2
    assert stats.chunk_count >= 2

    detail = await fake_service.get_document("alpha")
    assert detail.document_id == "alpha"
    assert detail.chunks[0].metadata.get("title") == "Alpha"
    assert detail.chunks[0].metadata.get("language") == "pt-br"
    assert detail.chunks[0].metadata.get("filename") == "alpha.md"


async def test_load_corpus_skips_already_indexed(
    tmp_path: Path, fake_service: SearchService
) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "only.md").write_text(
        "---\ntitle: Only\n---\n\nConteúdo único para reexecução.\n",
        encoding="utf-8",
    )

    first = await load_corpus(corpus, fake_service)
    second = await load_corpus(corpus, fake_service)

    assert first == 1
    assert second == 0
    assert fake_service.stats().document_count == 1


async def test_load_corpus_missing_dir_returns_zero(
    tmp_path: Path, fake_service: SearchService
) -> None:
    missing = tmp_path / "inexistente"
    added = await load_corpus(missing, fake_service)
    assert added == 0
    assert fake_service.stats().document_count == 0


async def test_load_corpus_ignores_empty_body(tmp_path: Path, fake_service: SearchService) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "empty.md").write_text(
        "---\ntitle: Empty\n---\n\n",
        encoding="utf-8",
    )

    added = await load_corpus(corpus, fake_service)
    assert added == 0
