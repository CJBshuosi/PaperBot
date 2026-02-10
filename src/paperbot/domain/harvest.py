# src/paperbot/domain/harvest.py
"""
Paper harvesting domain models.

Contains data structures for paper collection from multiple sources:
- HarvestedPaper: Unified paper format from any source
- HarvestSource: Enum of supported paper sources
- HarvestResult: Result from a single harvester
- HarvestRunResult: Aggregated result from all harvesters
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class HarvestSource(str, Enum):
    """Supported paper data sources."""

    ARXIV = "arxiv"
    SEMANTIC_SCHOLAR = "semantic_scholar"
    OPENALEX = "openalex"


@dataclass
class HarvestedPaper:
    """
    Unified paper format from any harvest source.

    Required fields: title, source
    All other fields are optional to handle varying API responses.
    """

    title: str
    source: HarvestSource
    abstract: str = ""
    authors: List[str] = field(default_factory=list)
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    semantic_scholar_id: Optional[str] = None
    openalex_id: Optional[str] = None
    year: Optional[int] = None
    venue: Optional[str] = None
    publication_date: Optional[str] = None
    citation_count: int = 0
    url: Optional[str] = None
    pdf_url: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    fields_of_study: List[str] = field(default_factory=list)
    source_rank: Optional[int] = None

    def compute_title_hash(self) -> str:
        """Compute normalized title hash for deduplication."""
        normalized = self.title.lower()
        normalized = re.sub(r"[^\w\s]", "", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return hashlib.sha256(normalized.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "title": self.title,
            "source": self.source.value,
            "abstract": self.abstract,
            "authors": self.authors,
            "doi": self.doi,
            "arxiv_id": self.arxiv_id,
            "semantic_scholar_id": self.semantic_scholar_id,
            "openalex_id": self.openalex_id,
            "year": self.year,
            "venue": self.venue,
            "publication_date": self.publication_date,
            "citation_count": self.citation_count,
            "url": self.url,
            "pdf_url": self.pdf_url,
            "keywords": self.keywords,
            "fields_of_study": self.fields_of_study,
            "source_rank": self.source_rank,
            "title_hash": self.compute_title_hash(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HarvestedPaper":
        """Create instance from dictionary."""
        source = data.get("source", "")
        if isinstance(source, str):
            source = HarvestSource(source)
        return cls(
            title=data.get("title", ""),
            source=source,
            abstract=data.get("abstract", ""),
            authors=data.get("authors", []),
            doi=data.get("doi"),
            arxiv_id=data.get("arxiv_id"),
            semantic_scholar_id=data.get("semantic_scholar_id"),
            openalex_id=data.get("openalex_id"),
            year=data.get("year"),
            venue=data.get("venue"),
            publication_date=data.get("publication_date"),
            citation_count=data.get("citation_count", 0),
            url=data.get("url"),
            pdf_url=data.get("pdf_url"),
            keywords=data.get("keywords", []),
            fields_of_study=data.get("fields_of_study", []),
            source_rank=data.get("source_rank"),
        )


@dataclass
class HarvestResult:
    """Result from a single harvester."""

    source: HarvestSource
    papers: List[HarvestedPaper]
    total_found: int
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        """Whether the harvest was successful."""
        return self.error is None


@dataclass
class HarvestRunResult:
    """Aggregated result from all harvesters in a harvest run."""

    run_id: str
    status: str  # running/success/partial/failed
    papers_found: int
    papers_new: int
    papers_deduplicated: int
    source_results: Dict[HarvestSource, HarvestResult]
    started_at: datetime
    ended_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "run_id": self.run_id,
            "status": self.status,
            "papers_found": self.papers_found,
            "papers_new": self.papers_new,
            "papers_deduplicated": self.papers_deduplicated,
            "sources": {
                source.value: {
                    "papers": len(result.papers),
                    "total_found": result.total_found,
                    "error": result.error,
                }
                for source, result in self.source_results.items()
            },
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
        }
