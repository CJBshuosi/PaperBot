"""PaperIdentity value object for unified external ID tracking."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PaperIdentity:
    """Immutable (source, external_id) pair identifying a paper in an external system."""

    source: str  # "semantic_scholar" | "arxiv" | "openalex" | "doi" | "papers_cool"
    external_id: str  # unique ID within that source

    def __post_init__(self) -> None:
        object.__setattr__(self, "source", (self.source or "").strip().lower())
        object.__setattr__(self, "external_id", (self.external_id or "").strip())

    def __bool__(self) -> bool:
        return bool(self.source and self.external_id)
