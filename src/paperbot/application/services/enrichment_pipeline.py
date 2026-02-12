"""EnrichmentPipeline — Chain of Responsibility for paper enrichment.

Each step processes a paper and can add judge scores, summaries,
repo discovery results, etc.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@dataclass
class EnrichmentContext:
    """Shared context passed through the pipeline."""

    query: str = ""
    user_id: str = "default"
    track_id: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class EnrichmentStep(Protocol):
    """Single enrichment step."""

    async def process(self, paper: Dict[str, Any], context: EnrichmentContext) -> None:
        """Mutate *paper* dict in-place with enrichment data."""
        ...


class EnrichmentPipeline:
    """Runs a chain of EnrichmentStep instances over a list of papers."""

    def __init__(self, steps: Optional[List[EnrichmentStep]] = None):
        self.steps: List[EnrichmentStep] = [s for s in (steps or []) if s is not None]

    async def run(
        self,
        papers: List[Dict[str, Any]],
        context: Optional[EnrichmentContext] = None,
    ) -> None:
        ctx = context or EnrichmentContext()
        for paper in papers:
            for step in self.steps:
                try:
                    await step.process(paper, ctx)
                except Exception as e:
                    title = str(paper.get("title", ""))[:60]
                    step_name = type(step).__name__
                    logger.warning(f"Enrichment step {step_name} failed for '{title}': {e}")
