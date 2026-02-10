"""
PaperStore integration tests.

Tests paper storage, deduplication, search, and library functionality.
"""

import pytest
from datetime import datetime, timezone

from paperbot.domain.harvest import HarvestedPaper, HarvestSource
from paperbot.infrastructure.stores.paper_store import PaperStore, paper_to_dict


@pytest.fixture
def paper_store(tmp_path):
    """Create a PaperStore with a temporary SQLite database."""
    db_url = f"sqlite:///{tmp_path / 'test_papers.db'}"
    store = PaperStore(db_url=db_url, auto_create_schema=True)
    yield store
    store.close()


class TestPaperStoreUpsert:
    """Tests for paper upsert functionality."""

    def test_upsert_single_paper(self, paper_store):
        """Upsert a single paper."""
        paper = HarvestedPaper(
            title="Test Paper",
            source=HarvestSource.ARXIV,
            abstract="Test abstract",
            authors=["Alice", "Bob"],
            doi="10.1234/test",
            year=2023,
            citation_count=10,
        )

        new_count, updated_count = paper_store.upsert_papers_batch([paper])

        assert new_count == 1
        assert updated_count == 0

    def test_upsert_multiple_papers(self, paper_store):
        """Upsert multiple papers."""
        papers = [
            HarvestedPaper(
                title=f"Paper {i}",
                source=HarvestSource.ARXIV,
                doi=f"10.1234/paper{i}",
                year=2023,
            )
            for i in range(5)
        ]

        new_count, updated_count = paper_store.upsert_papers_batch(papers)

        assert new_count == 5
        assert updated_count == 0
        assert paper_store.get_paper_count() == 5

    def test_upsert_deduplicates_by_doi(self, paper_store):
        """Papers with same DOI are deduplicated."""
        paper1 = HarvestedPaper(
            title="Original Title",
            source=HarvestSource.ARXIV,
            doi="10.1234/same-doi",
            citation_count=10,
        )
        paper2 = HarvestedPaper(
            title="Different Title",
            source=HarvestSource.SEMANTIC_SCHOLAR,
            doi="10.1234/same-doi",
            citation_count=20,
        )

        new1, _ = paper_store.upsert_papers_batch([paper1])
        new2, updated2 = paper_store.upsert_papers_batch([paper2])

        assert new1 == 1
        assert new2 == 0
        assert updated2 == 1
        assert paper_store.get_paper_count() == 1

    def test_upsert_deduplicates_by_arxiv_id(self, paper_store):
        """Papers with same arXiv ID are deduplicated."""
        paper1 = HarvestedPaper(
            title="Paper 1",
            source=HarvestSource.ARXIV,
            arxiv_id="2301.12345",
        )
        paper2 = HarvestedPaper(
            title="Paper 1 Variant",
            source=HarvestSource.SEMANTIC_SCHOLAR,
            arxiv_id="2301.12345",
            doi="10.1234/new-doi",  # New identifier
        )

        paper_store.upsert_papers_batch([paper1])
        new_count, updated_count = paper_store.upsert_papers_batch([paper2])

        assert new_count == 0
        assert updated_count == 1

        # DOI should be merged into existing record
        papers, _ = paper_store.search_papers(query="Paper 1")
        assert len(papers) == 1
        assert papers[0].doi == "10.1234/new-doi"

    def test_upsert_deduplicates_by_title_hash(self, paper_store):
        """Papers with same normalized title are deduplicated."""
        paper1 = HarvestedPaper(
            title="Deep Learning for NLP",
            source=HarvestSource.ARXIV,
        )
        paper2 = HarvestedPaper(
            title="DEEP LEARNING FOR NLP",  # Same title, different case
            source=HarvestSource.OPENALEX,
            doi="10.1234/dedup-test",
        )

        paper_store.upsert_papers_batch([paper1])
        new_count, updated_count = paper_store.upsert_papers_batch([paper2])

        assert new_count == 0
        assert updated_count == 1
        assert paper_store.get_paper_count() == 1

    def test_upsert_merges_metadata(self, paper_store):
        """Upsert merges metadata from duplicate papers."""
        paper1 = HarvestedPaper(
            title="Merge Test",
            source=HarvestSource.ARXIV,
            doi="10.1234/merge",
            abstract="Short",
            citation_count=10,
            keywords=["ML"],
        )
        paper2 = HarvestedPaper(
            title="Merge Test",
            source=HarvestSource.SEMANTIC_SCHOLAR,
            doi="10.1234/merge",
            abstract="A much longer abstract with more details",
            citation_count=20,
            keywords=["AI"],
            semantic_scholar_id="s2-123",
        )

        paper_store.upsert_papers_batch([paper1])
        paper_store.upsert_papers_batch([paper2])

        papers, _ = paper_store.search_papers(query="Merge Test")
        assert len(papers) == 1
        paper = papers[0]

        # Longer abstract preserved
        assert "longer" in paper.abstract
        # Higher citation count preserved
        assert paper.citation_count == 20
        # New identifier merged
        assert paper.semantic_scholar_id == "s2-123"


class TestPaperStoreSearch:
    """Tests for paper search functionality."""

    @pytest.fixture(autouse=True)
    def setup_papers(self, paper_store):
        """Add test papers to the store."""
        self.store = paper_store
        papers = [
            HarvestedPaper(
                title="Deep Learning for Natural Language Processing",
                source=HarvestSource.ARXIV,
                abstract="A study on transformers and attention mechanisms",
                doi="10.1234/nlp",
                year=2023,
                venue="NeurIPS",
                citation_count=100,
            ),
            HarvestedPaper(
                title="Computer Vision with Convolutional Networks",
                source=HarvestSource.SEMANTIC_SCHOLAR,
                abstract="CNN architectures for image classification",
                doi="10.1234/cv",
                year=2022,
                venue="CVPR",
                citation_count=200,
            ),
            HarvestedPaper(
                title="Reinforcement Learning in Robotics",
                source=HarvestSource.OPENALEX,
                abstract="RL algorithms for robot control",
                doi="10.1234/rl",
                year=2024,
                venue="ICRA",
                citation_count=50,
            ),
            HarvestedPaper(
                title="Security Analysis of Machine Learning Systems",
                source=HarvestSource.ARXIV,
                abstract="Adversarial attacks on deep learning models",
                doi="10.1234/security",
                year=2023,
                venue="CCS",
                citation_count=75,
            ),
        ]
        paper_store.upsert_papers_batch(papers)

    def test_search_by_query(self):
        """Search papers by query string."""
        papers, total = self.store.search_papers(query="deep learning")

        assert total >= 1
        assert any("Deep Learning" in p.title for p in papers)

    def test_search_by_year_range(self):
        """Search papers within year range."""
        papers, total = self.store.search_papers(year_from=2023, year_to=2024)

        assert all(2023 <= p.year <= 2024 for p in papers)
        assert total >= 2

    def test_search_by_venue(self):
        """Search papers by venue."""
        papers, total = self.store.search_papers(venues=["NeurIPS"])

        assert total >= 1
        assert all("NeurIPS" in (p.venue or "") for p in papers)

    def test_search_by_min_citations(self):
        """Search papers with minimum citations."""
        papers, total = self.store.search_papers(min_citations=100)

        assert all(p.citation_count >= 100 for p in papers)
        assert total >= 1

    def test_search_by_source(self):
        """Search papers by source."""
        papers, total = self.store.search_papers(sources=["arxiv"])

        assert all(p.primary_source == "arxiv" for p in papers)

    def test_search_sort_by_citations(self):
        """Search results sorted by citation count."""
        papers, _ = self.store.search_papers(
            sort_by="citation_count", sort_order="desc"
        )

        # Verify descending order
        for i in range(len(papers) - 1):
            assert (papers[i].citation_count or 0) >= (papers[i + 1].citation_count or 0)

    def test_search_sort_by_year(self):
        """Search results sorted by year."""
        papers, _ = self.store.search_papers(sort_by="year", sort_order="asc")

        # Verify ascending order
        for i in range(len(papers) - 1):
            if papers[i].year and papers[i + 1].year:
                assert papers[i].year <= papers[i + 1].year

    def test_search_pagination(self):
        """Search with pagination."""
        all_papers, total = self.store.search_papers(limit=100)

        # Get first page
        page1, _ = self.store.search_papers(limit=2, offset=0)
        assert len(page1) == 2

        # Get second page
        page2, _ = self.store.search_papers(limit=2, offset=2)

        # Pages should not overlap
        page1_ids = {p.id for p in page1}
        page2_ids = {p.id for p in page2}
        assert page1_ids.isdisjoint(page2_ids)

    def test_search_combined_filters(self):
        """Search with multiple filters combined."""
        papers, total = self.store.search_papers(
            query="learning",
            year_from=2023,
            min_citations=50,
            sort_by="citation_count",
            sort_order="desc",
        )

        for paper in papers:
            assert paper.year >= 2023
            assert paper.citation_count >= 50

    def test_search_no_results(self):
        """Search with no matching results."""
        papers, total = self.store.search_papers(query="xyznonexistent123")

        assert papers == []
        assert total == 0


class TestPaperStoreHarvestRun:
    """Tests for harvest run tracking."""

    def test_create_harvest_run(self, paper_store):
        """Create a harvest run record."""
        run = paper_store.create_harvest_run(
            run_id="test-run-001",
            keywords=["machine learning", "deep learning"],
            venues=["NeurIPS", "ICML"],
            sources=["arxiv", "semantic_scholar"],
            max_results_per_source=50,
        )

        assert run.run_id == "test-run-001"
        assert run.status == "running"
        assert run.get_keywords() == ["machine learning", "deep learning"]
        assert run.get_venues() == ["NeurIPS", "ICML"]
        assert run.get_sources() == ["arxiv", "semantic_scholar"]
        assert run.max_results_per_source == 50

    def test_update_harvest_run(self, paper_store):
        """Update a harvest run record."""
        paper_store.create_harvest_run(
            run_id="test-run-002",
            keywords=["test"],
            venues=[],
            sources=["arxiv"],
            max_results_per_source=50,
        )

        updated = paper_store.update_harvest_run(
            run_id="test-run-002",
            status="success",
            papers_found=100,
            papers_new=80,
            papers_deduplicated=20,
        )

        assert updated is not None
        assert updated.status == "success"
        assert updated.papers_found == 100
        assert updated.papers_new == 80
        assert updated.papers_deduplicated == 20
        assert updated.ended_at is not None

    def test_update_harvest_run_with_errors(self, paper_store):
        """Update harvest run with error information."""
        paper_store.create_harvest_run(
            run_id="test-run-003",
            keywords=["test"],
            venues=[],
            sources=["arxiv", "semantic_scholar"],
            max_results_per_source=50,
        )

        errors = {"semantic_scholar": "Rate limit exceeded"}
        updated = paper_store.update_harvest_run(
            run_id="test-run-003",
            status="partial",
            errors=errors,
        )

        assert updated.status == "partial"
        assert updated.get_errors() == errors

    def test_get_harvest_run(self, paper_store):
        """Retrieve a harvest run by ID."""
        paper_store.create_harvest_run(
            run_id="test-run-004",
            keywords=["retrieval test"],
            venues=["SIGIR"],
            sources=["openalex"],
            max_results_per_source=25,
        )

        run = paper_store.get_harvest_run("test-run-004")

        assert run is not None
        assert run.run_id == "test-run-004"
        assert run.get_keywords() == ["retrieval test"]

    def test_get_harvest_run_not_found(self, paper_store):
        """Get non-existent harvest run returns None."""
        run = paper_store.get_harvest_run("nonexistent-run")
        assert run is None

    def test_list_harvest_runs(self, paper_store):
        """List harvest runs."""
        for i in range(3):
            paper_store.create_harvest_run(
                run_id=f"list-test-{i}",
                keywords=[f"keyword{i}"],
                venues=[],
                sources=["arxiv"],
                max_results_per_source=50,
            )

        runs = paper_store.list_harvest_runs(limit=10)

        assert len(runs) >= 3
        # Should be sorted by started_at descending
        for i in range(len(runs) - 1):
            if runs[i].started_at and runs[i + 1].started_at:
                assert runs[i].started_at >= runs[i + 1].started_at

    def test_list_harvest_runs_by_status(self, paper_store):
        """List harvest runs filtered by status."""
        paper_store.create_harvest_run(
            run_id="status-test-1",
            keywords=["test"],
            venues=[],
            sources=["arxiv"],
            max_results_per_source=50,
        )
        paper_store.update_harvest_run("status-test-1", status="success")

        paper_store.create_harvest_run(
            run_id="status-test-2",
            keywords=["test"],
            venues=[],
            sources=["arxiv"],
            max_results_per_source=50,
        )
        # Remains "running"

        success_runs = paper_store.list_harvest_runs(status="success")
        running_runs = paper_store.list_harvest_runs(status="running")

        assert any(r.run_id == "status-test-1" for r in success_runs)
        assert any(r.run_id == "status-test-2" for r in running_runs)


class TestPaperStoreLibrary:
    """Tests for user library functionality."""

    def test_get_paper_by_id(self, paper_store):
        """Get paper by ID."""
        paper = HarvestedPaper(
            title="Get By ID Test",
            source=HarvestSource.ARXIV,
            doi="10.1234/getbyid",
        )
        paper_store.upsert_papers_batch([paper])

        papers, _ = paper_store.search_papers(query="Get By ID")
        assert len(papers) == 1

        retrieved = paper_store.get_paper_by_id(papers[0].id)
        assert retrieved is not None
        assert retrieved.title == "Get By ID Test"

    def test_get_paper_by_id_not_found(self, paper_store):
        """Get non-existent paper returns None."""
        paper = paper_store.get_paper_by_id(99999)
        assert paper is None

    def test_paper_to_dict(self, paper_store):
        """paper_to_dict converts model correctly."""
        paper = HarvestedPaper(
            title="Dict Test",
            source=HarvestSource.SEMANTIC_SCHOLAR,
            abstract="Test abstract",
            authors=["Alice", "Bob"],
            doi="10.1234/dict",
            year=2023,
            venue="ICML",
            citation_count=42,
            keywords=["ML"],
            fields_of_study=["CS"],
        )
        paper_store.upsert_papers_batch([paper])

        papers, _ = paper_store.search_papers(query="Dict Test")
        result = paper_to_dict(papers[0])

        assert result["title"] == "Dict Test"
        assert result["abstract"] == "Test abstract"
        assert result["authors"] == ["Alice", "Bob"]
        assert result["doi"] == "10.1234/dict"
        assert result["year"] == 2023
        assert result["venue"] == "ICML"
        assert result["citation_count"] == 42
        assert result["primary_source"] == "semantic_scholar"

    def test_get_paper_count(self, paper_store):
        """Get total paper count."""
        initial_count = paper_store.get_paper_count()

        papers = [
            HarvestedPaper(
                title=f"Count Test {i}",
                source=HarvestSource.ARXIV,
                doi=f"10.1234/count{i}",
            )
            for i in range(3)
        ]
        paper_store.upsert_papers_batch(papers)

        new_count = paper_store.get_paper_count()
        assert new_count == initial_count + 3


class TestPaperStoreEdgeCases:
    """Tests for edge cases and error handling."""

    def test_upsert_empty_list(self, paper_store):
        """Upsert empty list does nothing."""
        new_count, updated_count = paper_store.upsert_papers_batch([])

        assert new_count == 0
        assert updated_count == 0

    def test_upsert_paper_without_identifiers(self, paper_store):
        """Upsert paper with only title (uses title hash)."""
        paper = HarvestedPaper(
            title="No Identifiers Paper",
            source=HarvestSource.ARXIV,
        )

        new_count, _ = paper_store.upsert_papers_batch([paper])
        assert new_count == 1

        # Second upsert with same title should update
        paper2 = HarvestedPaper(
            title="No Identifiers Paper",
            source=HarvestSource.SEMANTIC_SCHOLAR,
            citation_count=10,
        )

        new_count, updated_count = paper_store.upsert_papers_batch([paper2])
        assert new_count == 0
        assert updated_count == 1

    def test_search_with_special_characters(self, paper_store):
        """Search handles special characters."""
        paper = HarvestedPaper(
            title="Test: A Paper with Special (Characters) & Symbols!",
            source=HarvestSource.ARXIV,
            doi="10.1234/special",
        )
        paper_store.upsert_papers_batch([paper])

        # Search with part of title (single word matches more reliably)
        papers, total = paper_store.search_papers(query="Special")
        assert total >= 1
        assert any("Special" in p.title for p in papers)

    def test_upsert_paper_with_unicode(self, paper_store):
        """Upsert paper with unicode characters."""
        paper = HarvestedPaper(
            title="机器学习论文 - Machine Learning Paper",
            source=HarvestSource.ARXIV,
            abstract="This paper discusses 深度学习 (deep learning)",
            authors=["张三", "李四"],
            doi="10.1234/unicode",
        )

        new_count, _ = paper_store.upsert_papers_batch([paper])
        assert new_count == 1

        papers, _ = paper_store.search_papers(query="Machine Learning")
        assert len(papers) == 1
        assert "机器学习" in papers[0].title

    def test_upsert_paper_with_long_abstract(self, paper_store):
        """Upsert paper with very long abstract."""
        long_abstract = "Lorem ipsum " * 1000  # ~12000 characters

        paper = HarvestedPaper(
            title="Long Abstract Paper",
            source=HarvestSource.ARXIV,
            abstract=long_abstract,
            doi="10.1234/long",
        )

        new_count, _ = paper_store.upsert_papers_batch([paper])
        assert new_count == 1

        papers, _ = paper_store.search_papers(query="Long Abstract")
        assert papers[0].abstract == long_abstract
