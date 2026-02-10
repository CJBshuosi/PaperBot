# src/paperbot/application/services/paper_deduplicator.py
"""
Paper deduplication service.

Multi-strategy deduplication for papers from multiple sources.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

from paperbot.domain.harvest import HarvestedPaper

logger = logging.getLogger(__name__)


class PaperDeduplicator:
    """
    Multi-strategy paper deduplication.

    Priority order:
    1. DOI (most reliable)
    2. arXiv ID
    3. Semantic Scholar ID
    4. OpenAlex ID
    5. Normalized title hash (fallback)

    When duplicates are found, metadata is merged to preserve
    the most complete information from all sources.
    """

    def __init__(self):
        self._doi_index: Dict[str, int] = {}
        self._arxiv_index: Dict[str, int] = {}
        self._s2_index: Dict[str, int] = {}
        self._openalex_index: Dict[str, int] = {}
        self._title_hash_index: Dict[str, int] = {}

    def reset(self) -> None:
        """Clear all indexes for a fresh deduplication run."""
        self._doi_index.clear()
        self._arxiv_index.clear()
        self._s2_index.clear()
        self._openalex_index.clear()
        self._title_hash_index.clear()

    def deduplicate(
        self,
        papers: List[HarvestedPaper],
    ) -> Tuple[List[HarvestedPaper], int]:
        """
        Deduplicate papers in-memory.

        Args:
            papers: List of papers from all sources

        Returns:
            Tuple of (deduplicated papers, count of duplicates removed)
        """
        self.reset()
        unique_papers: List[HarvestedPaper] = []
        duplicates_count = 0

        for paper in papers:
            existing_idx = self._find_duplicate(paper)

            if existing_idx is not None:
                # Merge metadata into existing paper
                self._merge_paper(unique_papers[existing_idx], paper)
                duplicates_count += 1
            else:
                # Add new paper
                idx = len(unique_papers)
                self._index_paper(paper, idx)
                unique_papers.append(paper)

        logger.info(
            f"Deduplication complete: {len(papers)} → {len(unique_papers)} "
            f"({duplicates_count} duplicates removed)"
        )
        return unique_papers, duplicates_count

    def _find_duplicate(self, paper: HarvestedPaper) -> Optional[int]:
        """Find existing paper index if duplicate exists."""
        # 1. DOI match (most reliable)
        if paper.doi:
            doi_lower = paper.doi.lower().strip()
            if doi_lower in self._doi_index:
                return self._doi_index[doi_lower]

        # 2. arXiv ID match
        if paper.arxiv_id:
            arxiv_lower = paper.arxiv_id.lower().strip()
            if arxiv_lower in self._arxiv_index:
                return self._arxiv_index[arxiv_lower]

        # 3. Semantic Scholar ID match
        if paper.semantic_scholar_id:
            s2_lower = paper.semantic_scholar_id.lower().strip()
            if s2_lower in self._s2_index:
                return self._s2_index[s2_lower]

        # 4. OpenAlex ID match
        if paper.openalex_id:
            openalex_lower = paper.openalex_id.lower().strip()
            if openalex_lower in self._openalex_index:
                return self._openalex_index[openalex_lower]

        # 5. Title hash match (fallback)
        title_hash = paper.compute_title_hash()
        if title_hash in self._title_hash_index:
            return self._title_hash_index[title_hash]

        return None

    def _index_paper(self, paper: HarvestedPaper, idx: int) -> None:
        """Add paper to all relevant indexes."""
        if paper.doi:
            self._doi_index[paper.doi.lower().strip()] = idx
        if paper.arxiv_id:
            self._arxiv_index[paper.arxiv_id.lower().strip()] = idx
        if paper.semantic_scholar_id:
            self._s2_index[paper.semantic_scholar_id.lower().strip()] = idx
        if paper.openalex_id:
            self._openalex_index[paper.openalex_id.lower().strip()] = idx

        title_hash = paper.compute_title_hash()
        self._title_hash_index[title_hash] = idx

    def _merge_paper(self, existing: HarvestedPaper, new: HarvestedPaper) -> None:
        """
        Merge metadata from new paper into existing.

        Strategy:
        - Fill in missing identifiers
        - Prefer longer/more complete text fields
        - Prefer higher citation counts
        - Merge lists (keywords, fields of study)
        """
        # Fill in missing identifiers
        if not existing.doi and new.doi:
            existing.doi = new.doi
            self._doi_index[new.doi.lower().strip()] = self._find_index(existing)
        if not existing.arxiv_id and new.arxiv_id:
            existing.arxiv_id = new.arxiv_id
            self._arxiv_index[new.arxiv_id.lower().strip()] = self._find_index(existing)
        if not existing.semantic_scholar_id and new.semantic_scholar_id:
            existing.semantic_scholar_id = new.semantic_scholar_id
            self._s2_index[new.semantic_scholar_id.lower().strip()] = self._find_index(existing)
        if not existing.openalex_id and new.openalex_id:
            existing.openalex_id = new.openalex_id
            self._openalex_index[new.openalex_id.lower().strip()] = self._find_index(existing)

        # Prefer longer abstract
        if len(new.abstract) > len(existing.abstract):
            existing.abstract = new.abstract

        # Prefer higher citation count
        if new.citation_count > existing.citation_count:
            existing.citation_count = new.citation_count

        # Fill in missing metadata
        if not existing.year and new.year:
            existing.year = new.year
        if not existing.venue and new.venue:
            existing.venue = new.venue
        if not existing.publication_date and new.publication_date:
            existing.publication_date = new.publication_date
        if not existing.url and new.url:
            existing.url = new.url
        if not existing.pdf_url and new.pdf_url:
            existing.pdf_url = new.pdf_url

        # Prefer more complete author list
        if len(new.authors) > len(existing.authors):
            existing.authors = new.authors

        # Merge keywords and fields (deduplicate)
        existing.keywords = list(set(existing.keywords + new.keywords))
        existing.fields_of_study = list(set(existing.fields_of_study + new.fields_of_study))

    def _find_index(self, paper: HarvestedPaper) -> int:
        """Find the index of a paper in the title hash index."""
        title_hash = paper.compute_title_hash()
        return self._title_hash_index.get(title_hash, -1)

    def is_duplicate(self, paper: HarvestedPaper) -> bool:
        """Check if a paper would be considered a duplicate."""
        return self._find_duplicate(paper) is not None
