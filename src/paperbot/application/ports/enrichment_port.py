"""EnrichmentPort — judge/summary read/write interface."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class EnrichmentPort(Protocol):
    """Abstract interface for paper enrichment (judge scores, summaries)."""

    def upsert_judge_scores_from_report(
        self, report: Dict[str, Any]
    ) -> Dict[str, int]: ...
