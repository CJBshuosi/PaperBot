# src/paperbot/application/ports/harvester_port.py
"""
Harvester port interface.

Defines the abstract interface for all paper harvesters.
"""

from __future__ import annotations

from typing import List, Optional, Protocol, runtime_checkable

from paperbot.domain.harvest import HarvestResult, HarvestSource


@runtime_checkable
class HarvesterPort(Protocol):
    """Abstract interface for all paper harvesters."""

    @property
    def source(self) -> HarvestSource:
        """Return the harvest source identifier."""
        ...

    async def search(
        self,
        query: str,
        *,
        max_results: int = 100,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        venues: Optional[List[str]] = None,
    ) -> HarvestResult:
        """
        Search for papers matching the query.

        Args:
            query: Search query string
            max_results: Maximum number of results to return
            year_from: Filter papers published on or after this year
            year_to: Filter papers published on or before this year
            venues: Filter papers from these venues (if supported by source)

        Returns:
            HarvestResult with papers and metadata
        """
        ...

    async def close(self) -> None:
        """Release resources (HTTP sessions, etc.)."""
        ...
