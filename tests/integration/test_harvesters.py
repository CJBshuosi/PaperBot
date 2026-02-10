"""
Harvester integration tests with mocked API responses.

Tests ArxivHarvester, SemanticScholarHarvester, and OpenAlexHarvester.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from paperbot.domain.harvest import HarvestSource
from paperbot.infrastructure.harvesters import (
    ArxivHarvester,
    SemanticScholarHarvester,
    OpenAlexHarvester,
)


# Sample API response data
ARXIV_ATOM_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2301.12345v1</id>
    <title>Attention Is All You Need</title>
    <summary>We propose a new architecture called Transformer.</summary>
    <author><name>Ashish Vaswani</name></author>
    <author><name>Noam Shazeer</name></author>
    <published>2023-01-15T00:00:00Z</published>
    <link href="http://arxiv.org/abs/2301.12345v1" rel="alternate" type="text/html"/>
    <link href="http://arxiv.org/pdf/2301.12345v1" rel="related" type="application/pdf"/>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2301.12346v1</id>
    <title>BERT: Pre-training of Deep Bidirectional Transformers</title>
    <summary>We introduce BERT for language understanding.</summary>
    <author><name>Jacob Devlin</name></author>
    <published>2023-01-16T00:00:00Z</published>
    <link href="http://arxiv.org/abs/2301.12346v1" rel="alternate" type="text/html"/>
    <link href="http://arxiv.org/pdf/2301.12346v1" rel="related" type="application/pdf"/>
  </entry>
</feed>
"""

S2_API_RESPONSE = {
    "data": [
        {
            "paperId": "s2-paper-001",
            "title": "Deep Learning for NLP",
            "abstract": "A comprehensive study on deep learning for NLP.",
            "year": 2023,
            "venue": "NeurIPS",
            "citationCount": 150,
            "authors": [{"name": "Alice Smith"}, {"name": "Bob Jones"}],
            "publicationDate": "2023-12-01",
            "externalIds": {"DOI": "10.1234/dl-nlp", "ArXiv": "2301.00001"},
            "fieldsOfStudy": ["Computer Science", "Machine Learning"],
            "url": "https://www.semanticscholar.org/paper/abc123",
            "openAccessPdf": {"url": "https://arxiv.org/pdf/2301.00001.pdf"},
        },
        {
            "paperId": "s2-paper-002",
            "title": "Reinforcement Learning in Robotics",
            "abstract": "RL algorithms for robotic control.",
            "year": 2022,
            "venue": "ICRA",
            "citationCount": 75,
            "authors": [{"name": "Charlie Brown"}],
            "publicationDate": "2022-06-15",
            "externalIds": {"DOI": "10.1234/rl-robot"},
            "fieldsOfStudy": ["Robotics", "AI"],
            "url": "https://www.semanticscholar.org/paper/def456",
            "openAccessPdf": None,
        },
    ]
}

OPENALEX_API_RESPONSE = {
    "meta": {"count": 2},
    "results": [
        {
            "id": "https://openalex.org/W123456",
            "title": "Computer Vision Advances",
            "abstract_inverted_index": {
                "Computer": [0],
                "vision": [1],
                "has": [2],
                "advanced": [3],
                "significantly": [4],
            },
            "publication_year": 2024,
            "cited_by_count": 200,
            "authorships": [
                {"author": {"display_name": "David Wilson"}},
                {"author": {"display_name": "Eve Martinez"}},
            ],
            "primary_location": {"source": {"display_name": "CVPR"}},
            "publication_date": "2024-01-10",
            "ids": {
                "doi": "https://doi.org/10.1234/cv-adv",
                "openalex": "https://openalex.org/W123456",
            },
            "open_access": {"oa_url": "https://example.com/paper.pdf"},
            "keywords": [{"display_name": "Computer Vision"}, {"display_name": "CNN"}],
            "concepts": [
                {"display_name": "Computer Science"},
                {"display_name": "Image Processing"},
            ],
        },
    ],
}


class TestArxivHarvester:
    """Tests for ArxivHarvester."""

    @pytest.fixture
    def harvester(self):
        """Create ArxivHarvester instance."""
        return ArxivHarvester()

    @pytest.mark.asyncio
    async def test_search_success(self, harvester):
        """Successful search returns papers."""
        with patch.object(harvester, "_get_session") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=ARXIV_ATOM_RESPONSE)

            mock_session.return_value.get = MagicMock(
                return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
            )

            result = await harvester.search("transformer", max_results=10)

            assert result.success
            assert len(result.papers) == 2
            assert result.source == HarvestSource.ARXIV

            # Check first paper
            paper1 = result.papers[0]
            assert "Attention" in paper1.title
            assert paper1.arxiv_id == "2301.12345"
            assert paper1.source == HarvestSource.ARXIV
            assert len(paper1.authors) >= 1

    @pytest.mark.asyncio
    async def test_search_api_error(self, harvester):
        """API error returns error result."""
        with patch.object(harvester, "_get_session") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 500

            mock_session.return_value.get = MagicMock(
                return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
            )

            result = await harvester.search("test")

            assert not result.success
            assert result.error is not None
            assert "500" in result.error

    @pytest.mark.asyncio
    async def test_search_with_year_filter(self, harvester):
        """Search with year filter builds correct query."""
        with patch.object(harvester, "_get_session") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=ARXIV_ATOM_RESPONSE)

            mock_get = MagicMock(
                return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
            )
            mock_session.return_value.get = mock_get

            await harvester.search(
                "deep learning",
                year_from=2020,
                year_to=2024,
                max_results=50,
            )

            # Verify query includes year filter
            call_args = mock_get.call_args
            params = call_args[1]["params"]
            assert "submittedDate" in params["search_query"]
            assert "20200101" in params["search_query"]
            assert "20241231" in params["search_query"]

    @pytest.mark.asyncio
    async def test_source_property(self, harvester):
        """source property returns ARXIV."""
        assert harvester.source == HarvestSource.ARXIV

    @pytest.mark.asyncio
    async def test_close(self, harvester):
        """close() releases resources."""
        mock_session = MagicMock()
        mock_session.closed = False
        mock_session.close = AsyncMock()
        harvester._session = mock_session

        await harvester.close()

        mock_session.close.assert_called_once()
        assert harvester._session is None


class TestSemanticScholarHarvester:
    """Tests for SemanticScholarHarvester."""

    @pytest.fixture
    def harvester(self):
        """Create SemanticScholarHarvester with mocked client."""
        mock_client = MagicMock()
        mock_client.search_papers = AsyncMock(return_value=S2_API_RESPONSE["data"])
        return SemanticScholarHarvester(client=mock_client)

    @pytest.mark.asyncio
    async def test_search_success(self, harvester):
        """Successful search returns papers."""
        result = await harvester.search("deep learning", max_results=10)

        assert result.success
        assert len(result.papers) == 2
        assert result.source == HarvestSource.SEMANTIC_SCHOLAR

        # Check first paper
        paper1 = result.papers[0]
        assert paper1.title == "Deep Learning for NLP"
        assert paper1.semantic_scholar_id == "s2-paper-001"
        assert paper1.doi == "10.1234/dl-nlp"
        assert paper1.arxiv_id == "2301.00001"
        assert paper1.year == 2023
        assert paper1.venue == "NeurIPS"
        assert paper1.citation_count == 150
        assert len(paper1.authors) == 2
        assert paper1.pdf_url is not None

    @pytest.mark.asyncio
    async def test_search_with_venue_filter(self, harvester):
        """Search filters by venue."""
        # Return all papers, then filter
        result = await harvester.search(
            "learning",
            venues=["NeurIPS"],
            max_results=10,
        )

        # Only NeurIPS paper should be returned
        assert all("NeurIPS" in (p.venue or "").lower() or "neurips" in (p.venue or "").lower()
                   for p in result.papers if p.venue)

    @pytest.mark.asyncio
    async def test_search_client_error(self, harvester):
        """Client error returns error result."""
        harvester.client.search_papers = AsyncMock(
            side_effect=Exception("API connection failed")
        )

        result = await harvester.search("test")

        assert not result.success
        assert "API connection failed" in result.error

    @pytest.mark.asyncio
    async def test_paper_without_optional_fields(self):
        """Paper handles missing optional fields."""
        mock_client = MagicMock()
        mock_client.search_papers = AsyncMock(
            return_value=[
                {
                    "paperId": "minimal-paper",
                    "title": "Minimal Paper",
                    "abstract": None,
                    "year": None,
                    "venue": None,
                    "citationCount": None,
                    "authors": [],
                    "externalIds": None,
                    "fieldsOfStudy": None,
                    "openAccessPdf": None,
                }
            ]
        )
        harvester = SemanticScholarHarvester(client=mock_client)

        result = await harvester.search("test")

        assert result.success
        paper = result.papers[0]
        assert paper.title == "Minimal Paper"
        assert paper.abstract == ""
        assert paper.citation_count == 0
        assert paper.authors == []

    @pytest.mark.asyncio
    async def test_source_property(self, harvester):
        """source property returns SEMANTIC_SCHOLAR."""
        assert harvester.source == HarvestSource.SEMANTIC_SCHOLAR


class TestOpenAlexHarvester:
    """Tests for OpenAlexHarvester."""

    @pytest.fixture
    def harvester(self):
        """Create OpenAlexHarvester instance."""
        return OpenAlexHarvester(email="test@example.com")

    @pytest.mark.asyncio
    async def test_search_success(self, harvester):
        """Successful search returns papers."""
        with patch.object(harvester, "_get_session") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=OPENALEX_API_RESPONSE)

            mock_session.return_value.get = MagicMock(
                return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
            )

            result = await harvester.search("computer vision", max_results=10)

            assert result.success
            assert len(result.papers) == 1
            assert result.source == HarvestSource.OPENALEX
            assert result.total_found == 2  # From meta.count

            # Check paper details
            paper = result.papers[0]
            assert paper.title == "Computer Vision Advances"
            assert paper.openalex_id == "W123456"
            assert paper.doi == "10.1234/cv-adv"
            assert paper.year == 2024
            assert paper.venue == "CVPR"
            assert paper.citation_count == 200
            assert len(paper.authors) == 2
            assert paper.pdf_url is not None

    @pytest.mark.asyncio
    async def test_search_api_error(self, harvester):
        """API error returns error result."""
        with patch.object(harvester, "_get_session") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 429  # Rate limit

            mock_session.return_value.get = MagicMock(
                return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
            )

            result = await harvester.search("test")

            assert not result.success
            assert "429" in result.error

    @pytest.mark.asyncio
    async def test_search_with_year_filter(self, harvester):
        """Search with year filter includes correct params."""
        with patch.object(harvester, "_get_session") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=OPENALEX_API_RESPONSE)

            mock_get = MagicMock(
                return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
            )
            mock_session.return_value.get = mock_get

            await harvester.search(
                "test",
                year_from=2020,
                year_to=2024,
            )

            # Verify filter params
            call_args = mock_get.call_args
            params = call_args[1]["params"]
            assert "filter" in params
            assert "publication_year" in params["filter"]

    @pytest.mark.asyncio
    async def test_abstract_reconstruction(self, harvester):
        """Abstract is reconstructed from inverted index."""
        with patch.object(harvester, "_get_session") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=OPENALEX_API_RESPONSE)

            mock_session.return_value.get = MagicMock(
                return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
            )

            result = await harvester.search("test")

            paper = result.papers[0]
            assert "Computer vision has advanced significantly" == paper.abstract

    @pytest.mark.asyncio
    async def test_email_polite_pool(self, harvester):
        """Email is included for polite pool."""
        with patch.object(harvester, "_get_session") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=OPENALEX_API_RESPONSE)

            mock_get = MagicMock(
                return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
            )
            mock_session.return_value.get = mock_get

            await harvester.search("test")

            call_args = mock_get.call_args
            params = call_args[1]["params"]
            assert params.get("mailto") == "test@example.com"

    @pytest.mark.asyncio
    async def test_source_property(self, harvester):
        """source property returns OPENALEX."""
        assert harvester.source == HarvestSource.OPENALEX

    @pytest.mark.asyncio
    async def test_close(self, harvester):
        """close() releases resources."""
        mock_session = MagicMock()
        mock_session.closed = False
        mock_session.close = AsyncMock()
        harvester._session = mock_session

        await harvester.close()

        mock_session.close.assert_called_once()
        assert harvester._session is None


class TestHarvesterInterface:
    """Tests to verify all harvesters implement the same interface."""

    @pytest.mark.asyncio
    async def test_all_harvesters_have_source_property(self):
        """All harvesters have source property."""
        harvesters = [
            ArxivHarvester(),
            SemanticScholarHarvester(),
            OpenAlexHarvester(),
        ]

        for harvester in harvesters:
            assert hasattr(harvester, "source")
            assert isinstance(harvester.source, HarvestSource)

    @pytest.mark.asyncio
    async def test_all_harvesters_have_search_method(self):
        """All harvesters have async search method."""
        harvesters = [
            ArxivHarvester(),
            SemanticScholarHarvester(),
            OpenAlexHarvester(),
        ]

        for harvester in harvesters:
            assert hasattr(harvester, "search")
            import inspect
            assert inspect.iscoroutinefunction(harvester.search)

    @pytest.mark.asyncio
    async def test_all_harvesters_have_close_method(self):
        """All harvesters have async close method."""
        harvesters = [
            ArxivHarvester(),
            SemanticScholarHarvester(),
            OpenAlexHarvester(),
        ]

        for harvester in harvesters:
            assert hasattr(harvester, "close")
            import inspect
            assert inspect.iscoroutinefunction(harvester.close)
