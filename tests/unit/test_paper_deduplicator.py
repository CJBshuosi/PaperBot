"""
PaperDeduplicator unit tests.
"""

import pytest

from paperbot.domain.harvest import HarvestedPaper, HarvestSource
from paperbot.application.services.paper_deduplicator import PaperDeduplicator


class TestPaperDeduplicator:
    """PaperDeduplicator tests."""

    def setup_method(self):
        """Reset deduplicator before each test."""
        self.deduplicator = PaperDeduplicator()

    def test_deduplicate_empty_list(self):
        """Empty list returns empty result."""
        unique, count = self.deduplicator.deduplicate([])
        assert unique == []
        assert count == 0

    def test_deduplicate_single_paper(self):
        """Single paper returns unchanged."""
        paper = HarvestedPaper(
            title="Test Paper",
            source=HarvestSource.ARXIV,
            doi="10.1234/test",
        )
        unique, count = self.deduplicator.deduplicate([paper])
        assert len(unique) == 1
        assert count == 0
        assert unique[0].title == "Test Paper"

    def test_deduplicate_by_doi(self):
        """Papers with same DOI are deduplicated."""
        paper1 = HarvestedPaper(
            title="Paper Version 1",
            source=HarvestSource.ARXIV,
            doi="10.1234/same-doi",
            abstract="Short abstract",
        )
        paper2 = HarvestedPaper(
            title="Paper Version 2",
            source=HarvestSource.SEMANTIC_SCHOLAR,
            doi="10.1234/same-doi",
            abstract="A much longer and more detailed abstract",
        )

        unique, count = self.deduplicator.deduplicate([paper1, paper2])

        assert len(unique) == 1
        assert count == 1
        # Longer abstract should be preserved
        assert "longer" in unique[0].abstract

    def test_deduplicate_by_arxiv_id(self):
        """Papers with same arXiv ID are deduplicated."""
        paper1 = HarvestedPaper(
            title="Paper 1",
            source=HarvestSource.ARXIV,
            arxiv_id="2301.12345",
        )
        paper2 = HarvestedPaper(
            title="Paper 1 (variant)",
            source=HarvestSource.SEMANTIC_SCHOLAR,
            arxiv_id="2301.12345",
        )

        unique, count = self.deduplicator.deduplicate([paper1, paper2])

        assert len(unique) == 1
        assert count == 1

    def test_deduplicate_by_semantic_scholar_id(self):
        """Papers with same Semantic Scholar ID are deduplicated."""
        paper1 = HarvestedPaper(
            title="Paper A",
            source=HarvestSource.SEMANTIC_SCHOLAR,
            semantic_scholar_id="abc123",
        )
        paper2 = HarvestedPaper(
            title="Paper A",
            source=HarvestSource.OPENALEX,
            semantic_scholar_id="abc123",
        )

        unique, count = self.deduplicator.deduplicate([paper1, paper2])

        assert len(unique) == 1
        assert count == 1

    def test_deduplicate_by_openalex_id(self):
        """Papers with same OpenAlex ID are deduplicated."""
        paper1 = HarvestedPaper(
            title="Paper B",
            source=HarvestSource.OPENALEX,
            openalex_id="W12345",
        )
        paper2 = HarvestedPaper(
            title="Paper B",
            source=HarvestSource.ARXIV,
            openalex_id="W12345",
        )

        unique, count = self.deduplicator.deduplicate([paper1, paper2])

        assert len(unique) == 1
        assert count == 1

    def test_deduplicate_by_title_hash(self):
        """Papers with same normalized title are deduplicated."""
        paper1 = HarvestedPaper(
            title="Deep Learning for NLP",
            source=HarvestSource.ARXIV,
        )
        paper2 = HarvestedPaper(
            title="DEEP LEARNING FOR NLP",  # Same title, different case
            source=HarvestSource.SEMANTIC_SCHOLAR,
        )

        unique, count = self.deduplicator.deduplicate([paper1, paper2])

        assert len(unique) == 1
        assert count == 1

    def test_deduplicate_merges_identifiers(self):
        """Deduplication merges identifiers from duplicates."""
        paper1 = HarvestedPaper(
            title="Test Paper",
            source=HarvestSource.ARXIV,
            arxiv_id="2301.12345",
        )
        paper2 = HarvestedPaper(
            title="Test Paper",
            source=HarvestSource.SEMANTIC_SCHOLAR,
            doi="10.1234/test",
            semantic_scholar_id="s2-123",
        )

        unique, count = self.deduplicator.deduplicate([paper1, paper2])

        assert len(unique) == 1
        assert unique[0].arxiv_id == "2301.12345"
        assert unique[0].doi == "10.1234/test"
        assert unique[0].semantic_scholar_id == "s2-123"

    def test_deduplicate_prefers_higher_citations(self):
        """Higher citation count is preserved during merge."""
        paper1 = HarvestedPaper(
            title="Cited Paper",
            source=HarvestSource.ARXIV,
            doi="10.1234/cited",
            citation_count=10,
        )
        paper2 = HarvestedPaper(
            title="Cited Paper",
            source=HarvestSource.SEMANTIC_SCHOLAR,
            doi="10.1234/cited",
            citation_count=50,
        )

        unique, count = self.deduplicator.deduplicate([paper1, paper2])

        assert len(unique) == 1
        assert unique[0].citation_count == 50

    def test_deduplicate_merges_keywords(self):
        """Keywords from all duplicates are merged."""
        paper1 = HarvestedPaper(
            title="ML Paper",
            source=HarvestSource.ARXIV,
            doi="10.1234/ml",
            keywords=["deep learning", "neural network"],
        )
        paper2 = HarvestedPaper(
            title="ML Paper",
            source=HarvestSource.OPENALEX,
            doi="10.1234/ml",
            keywords=["machine learning", "deep learning"],
        )

        unique, count = self.deduplicator.deduplicate([paper1, paper2])

        assert len(unique) == 1
        keywords = set(unique[0].keywords)
        assert "deep learning" in keywords
        assert "neural network" in keywords
        assert "machine learning" in keywords

    def test_deduplicate_prefers_longer_author_list(self):
        """Longer author list is preserved."""
        paper1 = HarvestedPaper(
            title="Multi-author Paper",
            source=HarvestSource.ARXIV,
            doi="10.1234/multi",
            authors=["Alice", "Bob"],
        )
        paper2 = HarvestedPaper(
            title="Multi-author Paper",
            source=HarvestSource.SEMANTIC_SCHOLAR,
            doi="10.1234/multi",
            authors=["Alice", "Bob", "Charlie", "Diana"],
        )

        unique, count = self.deduplicator.deduplicate([paper1, paper2])

        assert len(unique) == 1
        assert len(unique[0].authors) == 4

    def test_no_duplicates_different_papers(self):
        """Different papers are not deduplicated."""
        paper1 = HarvestedPaper(
            title="First Paper",
            source=HarvestSource.ARXIV,
            doi="10.1234/first",
        )
        paper2 = HarvestedPaper(
            title="Second Paper",
            source=HarvestSource.SEMANTIC_SCHOLAR,
            doi="10.1234/second",
        )
        paper3 = HarvestedPaper(
            title="Third Paper",
            source=HarvestSource.OPENALEX,
            arxiv_id="2301.99999",
        )

        unique, count = self.deduplicator.deduplicate([paper1, paper2, paper3])

        assert len(unique) == 3
        assert count == 0

    def test_is_duplicate_check(self):
        """is_duplicate correctly identifies duplicates."""
        paper1 = HarvestedPaper(
            title="Indexed Paper",
            source=HarvestSource.ARXIV,
            doi="10.1234/indexed",
        )

        # First, deduplicate to build index
        self.deduplicator.deduplicate([paper1])

        # Check duplicate
        paper2 = HarvestedPaper(
            title="Different Title",
            source=HarvestSource.SEMANTIC_SCHOLAR,
            doi="10.1234/indexed",  # Same DOI
        )
        assert self.deduplicator.is_duplicate(paper2) is True

        # Check non-duplicate
        paper3 = HarvestedPaper(
            title="New Paper",
            source=HarvestSource.OPENALEX,
            doi="10.1234/new",
        )
        assert self.deduplicator.is_duplicate(paper3) is False

    def test_reset_clears_indexes(self):
        """reset() clears all indexes."""
        paper = HarvestedPaper(
            title="Reset Test",
            source=HarvestSource.ARXIV,
            doi="10.1234/reset",
        )

        self.deduplicator.deduplicate([paper])
        assert self.deduplicator.is_duplicate(paper) is True

        self.deduplicator.reset()
        assert self.deduplicator.is_duplicate(paper) is False

    def test_case_insensitive_matching(self):
        """ID matching is case-insensitive."""
        paper1 = HarvestedPaper(
            title="Case Test",
            source=HarvestSource.ARXIV,
            doi="10.1234/UPPERCASE",
        )
        paper2 = HarvestedPaper(
            title="Case Test",
            source=HarvestSource.SEMANTIC_SCHOLAR,
            doi="10.1234/uppercase",  # lowercase
        )

        unique, count = self.deduplicator.deduplicate([paper1, paper2])

        assert len(unique) == 1
        assert count == 1
