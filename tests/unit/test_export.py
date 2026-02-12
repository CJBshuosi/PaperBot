"""Unit tests for BibTeX / RIS / Markdown paper export."""

from __future__ import annotations

import pytest

from paperbot.api.routes.research import (
    _dedup_citation_keys,
    _escape_bibtex,
    _make_citation_key,
    _paper_to_bibtex,
    _paper_to_markdown,
    _paper_to_ris,
)

# ---- fixtures ---------------------------------------------------------------

_PAPER_FULL = {
    "title": "Attention Is All You Need",
    "authors": ["Ashish Vaswani", "Noam Shazeer"],
    "year": 2017,
    "venue": "NeurIPS",
    "doi": "10.5555/3295222.3295349",
    "url": "https://papers.nips.cc/paper/7181",
    "arxiv_id": "1706.03762",
}

_PAPER_MINIMAL = {
    "title": "Some Draft",
    "authors": [],
    "year": None,
    "venue": None,
    "doi": None,
    "url": None,
    "arxiv_id": None,
}

_PAPER_CONF = {
    "title": "Conf Paper",
    "authors": ["Alice Smith"],
    "year": 2024,
    "venue": "Proceedings of ICML",
    "doi": None,
    "url": "https://example.com",
    "arxiv_id": None,
}


# ---- citation key -----------------------------------------------------------

class TestCitationKey:
    def test_normal(self):
        assert _make_citation_key(["John Smith", "Jane Doe"], 2025) == "smith2025"

    def test_single_name(self):
        assert _make_citation_key(["Madonna"], 2020) == "madonna2020"

    def test_empty_authors(self):
        assert _make_citation_key([], 2023) == "unknown2023"

    def test_no_year(self):
        assert _make_citation_key(["Alice"], None) == "alicend"


class TestDedupKeys:
    def test_no_collision(self):
        assert _dedup_citation_keys(["a", "b", "c"]) == ["a", "b", "c"]

    def test_collision(self):
        assert _dedup_citation_keys(["smith2025", "smith2025", "doe2025"]) == [
            "smith2025",
            "smith2025b",
            "doe2025",
        ]

    def test_triple_collision(self):
        result = _dedup_citation_keys(["x", "x", "x"])
        assert result == ["x", "xb", "xc"]


# ---- BibTeX -----------------------------------------------------------------

class TestBibtex:
    def test_full_paper(self):
        bib = _paper_to_bibtex(_PAPER_FULL, "vaswani2017")
        assert bib.startswith("@article{vaswani2017,")
        assert "title = {Attention Is All You Need}" in bib
        assert "author = {Ashish Vaswani and Noam Shazeer}" in bib
        assert "doi = {10.5555/3295222.3295349}" in bib
        assert "eprint = {1706.03762}" in bib
        assert "archiveprefix = {arXiv}" in bib

    def test_misc_without_doi(self):
        bib = _paper_to_bibtex(_PAPER_MINIMAL, "unknown_nd")
        assert bib.startswith("@misc{unknown_nd,")
        assert "doi" not in bib

    def test_escape(self):
        assert _escape_bibtex("a {b} c") == "a \\{b\\} c"


# ---- RIS --------------------------------------------------------------------

class TestRis:
    def test_journal_paper(self):
        ris = _paper_to_ris(_PAPER_FULL)
        assert ris.startswith("TY  - JOUR")
        assert "TI  - Attention Is All You Need" in ris
        assert "AU  - Ashish Vaswani" in ris
        assert "DO  - 10.5555/3295222.3295349" in ris
        assert "AN  - 1706.03762" in ris
        assert ris.strip().endswith("ER  -")

    def test_conference_paper(self):
        ris = _paper_to_ris(_PAPER_CONF)
        assert ris.startswith("TY  - CONF")

    def test_minimal(self):
        ris = _paper_to_ris(_PAPER_MINIMAL)
        assert "TY  - JOUR" in ris
        assert "DO" not in ris
        assert "AN" not in ris


# ---- Markdown ---------------------------------------------------------------

class TestMarkdown:
    def test_full_paper(self):
        md = _paper_to_markdown(_PAPER_FULL)
        assert "**Attention Is All You Need**" in md
        assert "Ashish Vaswani, Noam Shazeer" in md
        assert "(2017)" in md
        assert "[DOI]" in md
        assert "[arXiv]" in md

    def test_minimal(self):
        md = _paper_to_markdown(_PAPER_MINIMAL)
        assert "**Some Draft**" in md
        assert "(n.d.)" in md
        assert "[DOI]" not in md
