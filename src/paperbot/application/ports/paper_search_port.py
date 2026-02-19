"""SearchPort — unified search interface for all paper data sources."""

from __future__ import annotations

from typing import List, Optional, Protocol, runtime_checkable

from paperbot.domain.paper import PaperCandidate


@runtime_checkable
class SearchPort(Protocol):
    """Single data-source search adapter."""

    @property
    def source_name(self) -> str: ...

    async def search(
        self,
        query: str,
        *,
        max_results: int = 30,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
    ) -> List[PaperCandidate]: ...

    async def close(self) -> None: ...
