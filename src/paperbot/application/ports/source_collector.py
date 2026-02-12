"""Source collector contract shared by API and browser-based collectors."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Protocol, runtime_checkable


@dataclass
class SourceCollectRequest:
    source: str
    query: str
    max_results: int = 100
    session: Dict[str, Any] = field(default_factory=dict)
    strategy: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SourceCollectResult:
    source: str
    items: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    trace: Dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class SourceCollector(Protocol):
    """Unified source collection interface.

    Implementations can be plain API connectors or browser-driven collectors.
    """

    async def collect(self, req: SourceCollectRequest) -> SourceCollectResult: ...

    async def close(self) -> None: ...


class NullSourceCollector:
    """No-op collector for fallback paths and tests."""

    async def collect(self, req: SourceCollectRequest) -> SourceCollectResult:
        return SourceCollectResult(
            source=req.source,
            items=[],
            metadata={"reason": "null_source_collector"},
            trace={"strategy": req.strategy},
        )

    async def close(self) -> None:  # pragma: no cover
        return None
