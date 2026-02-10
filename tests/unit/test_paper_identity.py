from paperbot.domain.paper_identity import normalize_arxiv_id, normalize_doi, normalize_paper_id


def test_normalize_arxiv_id_from_urls_and_prefixes():
    assert normalize_arxiv_id("arXiv:2501.12345v2") == "2501.12345v2"
    assert normalize_arxiv_id("https://arxiv.org/abs/2501.12345") == "2501.12345"
    assert normalize_arxiv_id("https://arxiv.org/pdf/2501.12345.pdf") == "2501.12345"


def test_normalize_doi_from_url_or_raw():
    assert normalize_doi("https://doi.org/10.1145/123.456") == "10.1145/123.456"
    assert normalize_doi("10.48550/arXiv.2501.12345") == "10.48550/arxiv.2501.12345"


def test_normalize_paper_id_prefers_arxiv():
    assert normalize_paper_id("https://arxiv.org/abs/2501.12345") == "arxiv:2501.12345"
    assert normalize_paper_id("https://doi.org/10.1145/123.456") == "doi:10.1145/123.456"
