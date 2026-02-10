from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional, Protocol, Sequence

from paperbot.infrastructure.connectors.arxiv_connector import ArxivConnector
from paperbot.infrastructure.connectors.paperscool_connector import PapersCoolConnector


@dataclass
class TopicSearchRecord:
    source: str
    source_record_id: str
    title: str
    url: str
    source_branch: str
    external_url: str
    pdf_url: str
    authors: List[str]
    subject_or_venue: str
    published_at: str
    snippet: str
    keywords: List[str]
    pdf_stars: int
    kimi_stars: int


class TopicSearchSource(Protocol):
    name: str

    def search(
        self,
        *,
        query: str,
        branches: Sequence[str],
        show_per_branch: int,
    ) -> List[TopicSearchRecord]: ...


class TopicSearchSourceRegistry:
    def __init__(self) -> None:
        self._factories: Dict[str, Callable[[], TopicSearchSource]] = {}

    def register(self, name: str, factory: Callable[[], TopicSearchSource]) -> None:
        self._factories[name.strip().lower()] = factory

    def create(self, name: str) -> TopicSearchSource:
        key = name.strip().lower()
        if key not in self._factories:
            raise KeyError(f"Unknown topic search source: {name}")
        return self._factories[key]()

    def available(self) -> List[str]:
        return sorted(self._factories.keys())


class PapersCoolTopicSource:
    name = "papers_cool"

    def __init__(self, connector: Optional[PapersCoolConnector] = None):
        self.connector = connector or PapersCoolConnector()

    def search(
        self,
        *,
        query: str,
        branches: Sequence[str],
        show_per_branch: int,
    ) -> List[TopicSearchRecord]:
        rows: List[TopicSearchRecord] = []
        for branch in branches:
            records = self.connector.search(
                branch=branch,
                query=query,
                highlight=True,
                show=show_per_branch,
            )
            for record in records:
                rows.append(
                    TopicSearchRecord(
                        source=self.name,
                        source_record_id=record.paper_id,
                        title=record.title,
                        url=record.url,
                        source_branch=record.source_branch,
                        external_url=record.external_url,
                        pdf_url=record.pdf_url,
                        authors=record.authors,
                        subject_or_venue=record.subject_or_venue,
                        published_at=record.published_at,
                        snippet=record.snippet,
                        keywords=record.keywords,
                        pdf_stars=record.pdf_stars,
                        kimi_stars=record.kimi_stars,
                    )
                )
        return rows


class ArxivTopicSource:
    """arXiv public API as a TopicSearchSource."""

    name = "arxiv_api"

    def __init__(self, connector: Optional[ArxivConnector] = None):
        self.connector = connector or ArxivConnector()

    def search(
        self,
        *,
        query: str,
        branches: Sequence[str],
        show_per_branch: int,
    ) -> List[TopicSearchRecord]:
        records = self.connector.search(query=query, max_results=show_per_branch)
        return [
            TopicSearchRecord(
                source=self.name,
                source_record_id=r.arxiv_id,
                title=r.title,
                url=r.abs_url,
                source_branch="arxiv",
                external_url=r.abs_url,
                pdf_url=r.pdf_url,
                authors=r.authors,
                subject_or_venue="",
                published_at=r.published,
                snippet=r.summary[:500] if r.summary else "",
                keywords=[],
                pdf_stars=0,
                kimi_stars=0,
            )
            for r in records
        ]


def build_default_topic_source_registry(
    connector: Optional[PapersCoolConnector] = None,
) -> TopicSearchSourceRegistry:
    registry = TopicSearchSourceRegistry()
    registry.register("papers_cool", lambda: PapersCoolTopicSource(connector=connector))
    registry.register("arxiv_api", lambda: ArxivTopicSource())
    return registry


def dedupe_sources(sources: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for source in sources:
        key = (source or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out
