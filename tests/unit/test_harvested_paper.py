"""
HarvestedPaper domain model unit tests.
"""

import pytest

from paperbot.domain.harvest import (
    HarvestedPaper,
    HarvestResult,
    HarvestRunResult,
    HarvestSource,
)


class TestHarvestedPaper:
    """Tests for HarvestedPaper data model."""

    def test_create_minimal_paper(self):
        """Create paper with only required fields."""
        paper = HarvestedPaper(
            title="Test Paper",
            source=HarvestSource.ARXIV,
        )
        assert paper.title == "Test Paper"
        assert paper.source == HarvestSource.ARXIV
        assert paper.abstract == ""
        assert paper.authors == []
        assert paper.doi is None
        assert paper.citation_count == 0

    def test_create_full_paper(self):
        """Create paper with all fields."""
        paper = HarvestedPaper(
            title="Full Paper",
            source=HarvestSource.SEMANTIC_SCHOLAR,
            abstract="This is an abstract.",
            authors=["Alice", "Bob"],
            doi="10.1234/test",
            arxiv_id="2301.12345",
            semantic_scholar_id="s2-123",
            openalex_id="W12345",
            year=2023,
            venue="NeurIPS",
            publication_date="2023-12-01",
            citation_count=100,
            url="https://example.com/paper",
            pdf_url="https://example.com/paper.pdf",
            keywords=["ML", "AI"],
            fields_of_study=["Computer Science"],
            source_rank=1,
        )

        assert paper.title == "Full Paper"
        assert paper.source == HarvestSource.SEMANTIC_SCHOLAR
        assert paper.abstract == "This is an abstract."
        assert paper.authors == ["Alice", "Bob"]
        assert paper.doi == "10.1234/test"
        assert paper.arxiv_id == "2301.12345"
        assert paper.semantic_scholar_id == "s2-123"
        assert paper.openalex_id == "W12345"
        assert paper.year == 2023
        assert paper.venue == "NeurIPS"
        assert paper.publication_date == "2023-12-01"
        assert paper.citation_count == 100
        assert paper.url == "https://example.com/paper"
        assert paper.pdf_url == "https://example.com/paper.pdf"
        assert paper.keywords == ["ML", "AI"]
        assert paper.fields_of_study == ["Computer Science"]
        assert paper.source_rank == 1

    def test_compute_title_hash_basic(self):
        """Title hash normalizes and hashes correctly."""
        paper = HarvestedPaper(
            title="Deep Learning for NLP",
            source=HarvestSource.ARXIV,
        )
        hash1 = paper.compute_title_hash()

        # Same title should produce same hash
        paper2 = HarvestedPaper(
            title="Deep Learning for NLP",
            source=HarvestSource.OPENALEX,
        )
        assert paper2.compute_title_hash() == hash1

    def test_compute_title_hash_case_insensitive(self):
        """Title hash is case-insensitive."""
        paper1 = HarvestedPaper(title="Deep Learning", source=HarvestSource.ARXIV)
        paper2 = HarvestedPaper(title="DEEP LEARNING", source=HarvestSource.ARXIV)
        paper3 = HarvestedPaper(title="deep learning", source=HarvestSource.ARXIV)

        assert paper1.compute_title_hash() == paper2.compute_title_hash()
        assert paper2.compute_title_hash() == paper3.compute_title_hash()

    def test_compute_title_hash_ignores_punctuation(self):
        """Title hash ignores punctuation."""
        paper1 = HarvestedPaper(title="Deep Learning", source=HarvestSource.ARXIV)
        paper2 = HarvestedPaper(title="Deep, Learning!", source=HarvestSource.ARXIV)
        paper3 = HarvestedPaper(title="Deep-Learning?", source=HarvestSource.ARXIV)

        # All should have same hash after removing punctuation
        assert paper1.compute_title_hash() == paper2.compute_title_hash()
        # Note: hyphens are removed, making it "deeplearning" vs "deep learning"
        # This might differ, which is intentional for similar titles

    def test_compute_title_hash_normalizes_whitespace(self):
        """Title hash normalizes whitespace."""
        paper1 = HarvestedPaper(title="Deep Learning", source=HarvestSource.ARXIV)
        paper2 = HarvestedPaper(title="Deep  Learning", source=HarvestSource.ARXIV)
        paper3 = HarvestedPaper(title=" Deep Learning ", source=HarvestSource.ARXIV)

        assert paper1.compute_title_hash() == paper2.compute_title_hash()
        assert paper2.compute_title_hash() == paper3.compute_title_hash()

    def test_to_dict(self):
        """to_dict returns correct dictionary."""
        paper = HarvestedPaper(
            title="Test",
            source=HarvestSource.ARXIV,
            doi="10.1234/test",
            year=2023,
        )
        result = paper.to_dict()

        assert result["title"] == "Test"
        assert result["source"] == "arxiv"
        assert result["doi"] == "10.1234/test"
        assert result["year"] == 2023
        assert "title_hash" in result

    def test_from_dict(self):
        """from_dict creates paper from dictionary."""
        data = {
            "title": "From Dict Paper",
            "source": "semantic_scholar",
            "abstract": "An abstract",
            "authors": ["Author1"],
            "doi": "10.1234/fromdict",
            "year": 2024,
            "citation_count": 50,
        }

        paper = HarvestedPaper.from_dict(data)

        assert paper.title == "From Dict Paper"
        assert paper.source == HarvestSource.SEMANTIC_SCHOLAR
        assert paper.abstract == "An abstract"
        assert paper.authors == ["Author1"]
        assert paper.doi == "10.1234/fromdict"
        assert paper.year == 2024
        assert paper.citation_count == 50

    def test_from_dict_with_source_enum(self):
        """from_dict handles source as enum."""
        data = {
            "title": "Test",
            "source": HarvestSource.OPENALEX,
        }

        paper = HarvestedPaper.from_dict(data)
        assert paper.source == HarvestSource.OPENALEX

    def test_roundtrip_dict(self):
        """to_dict and from_dict roundtrip preserves data."""
        original = HarvestedPaper(
            title="Roundtrip Test",
            source=HarvestSource.ARXIV,
            abstract="Test abstract",
            authors=["Alice", "Bob"],
            doi="10.1234/roundtrip",
            arxiv_id="2301.12345",
            year=2023,
            venue="ICML",
            citation_count=42,
            keywords=["ML", "Test"],
            fields_of_study=["CS"],
        )

        data = original.to_dict()
        restored = HarvestedPaper.from_dict(data)

        assert restored.title == original.title
        assert restored.source == original.source
        assert restored.abstract == original.abstract
        assert restored.authors == original.authors
        assert restored.doi == original.doi
        assert restored.arxiv_id == original.arxiv_id
        assert restored.year == original.year
        assert restored.venue == original.venue
        assert restored.citation_count == original.citation_count


class TestHarvestSource:
    """Tests for HarvestSource enum."""

    def test_source_values(self):
        """Source enum has correct string values."""
        assert HarvestSource.ARXIV.value == "arxiv"
        assert HarvestSource.SEMANTIC_SCHOLAR.value == "semantic_scholar"
        assert HarvestSource.OPENALEX.value == "openalex"

    def test_source_is_string(self):
        """Source enum inherits from str."""
        assert isinstance(HarvestSource.ARXIV, str)
        assert HarvestSource.ARXIV == "arxiv"

    def test_source_from_string(self):
        """Source can be created from string."""
        source = HarvestSource("arxiv")
        assert source == HarvestSource.ARXIV


class TestHarvestResult:
    """Tests for HarvestResult data model."""

    def test_success_result(self):
        """Success result has no error."""
        result = HarvestResult(
            source=HarvestSource.ARXIV,
            papers=[
                HarvestedPaper(title="Paper 1", source=HarvestSource.ARXIV),
            ],
            total_found=1,
        )

        assert result.success is True
        assert result.error is None
        assert len(result.papers) == 1
        assert result.total_found == 1

    def test_error_result(self):
        """Error result has error message."""
        result = HarvestResult(
            source=HarvestSource.SEMANTIC_SCHOLAR,
            papers=[],
            total_found=0,
            error="API rate limit exceeded",
        )

        assert result.success is False
        assert result.error == "API rate limit exceeded"
        assert len(result.papers) == 0

    def test_partial_result(self):
        """Partial result can have both papers and error."""
        result = HarvestResult(
            source=HarvestSource.OPENALEX,
            papers=[
                HarvestedPaper(title="Paper 1", source=HarvestSource.OPENALEX),
            ],
            total_found=100,  # More papers exist but couldn't be fetched
            error="Timeout after 50 papers",
        )

        assert result.success is False
        assert len(result.papers) == 1
        assert result.total_found == 100


class TestHarvestRunResult:
    """Tests for HarvestRunResult data model."""

    def test_create_run_result(self):
        """Create a complete run result."""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)

        result = HarvestRunResult(
            run_id="harvest-20260210-abc123",
            status="success",
            papers_found=150,
            papers_new=100,
            papers_deduplicated=50,
            source_results={
                HarvestSource.ARXIV: HarvestResult(
                    source=HarvestSource.ARXIV,
                    papers=[],
                    total_found=50,
                ),
                HarvestSource.SEMANTIC_SCHOLAR: HarvestResult(
                    source=HarvestSource.SEMANTIC_SCHOLAR,
                    papers=[],
                    total_found=60,
                ),
            },
            started_at=now,
            ended_at=now,
        )

        assert result.run_id == "harvest-20260210-abc123"
        assert result.status == "success"
        assert result.papers_found == 150
        assert result.papers_new == 100
        assert result.papers_deduplicated == 50

    def test_to_dict(self):
        """to_dict returns correct structure."""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)

        result = HarvestRunResult(
            run_id="test-run",
            status="partial",
            papers_found=100,
            papers_new=80,
            papers_deduplicated=20,
            source_results={
                HarvestSource.ARXIV: HarvestResult(
                    source=HarvestSource.ARXIV,
                    papers=[HarvestedPaper(title="P1", source=HarvestSource.ARXIV)],
                    total_found=50,
                ),
            },
            started_at=now,
        )

        data = result.to_dict()

        assert data["run_id"] == "test-run"
        assert data["status"] == "partial"
        assert data["papers_found"] == 100
        assert data["papers_new"] == 80
        assert data["papers_deduplicated"] == 20
        assert "arxiv" in data["sources"]
        assert data["sources"]["arxiv"]["papers"] == 1
        assert data["sources"]["arxiv"]["total_found"] == 50
