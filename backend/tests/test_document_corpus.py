from services.document_service import DocumentService


def test_build_corpus_joins_files_with_separator():
    corpus = DocumentService.build_corpus(["alpha", "beta"], max_chars=1000)
    assert "alpha" in corpus
    assert "beta" in corpus
    assert "---" in corpus  # separator between files


def test_build_corpus_truncates_to_max_chars():
    big = "x" * 100_000
    corpus = DocumentService.build_corpus([big, big], max_chars=1000)
    assert len(corpus) <= 1000


def test_build_corpus_allocates_share_per_file():
    a = "a" * 10_000
    b = "b" * 10_000
    corpus = DocumentService.build_corpus([a, b], max_chars=1000)
    # Both files represented (proportional share, neither dominates)
    assert "a" in corpus and "b" in corpus


def test_build_corpus_handles_empty_list():
    assert DocumentService.build_corpus([], max_chars=1000) == ""
