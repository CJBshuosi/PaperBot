"""FeedbackPort — paper feedback read/write interface."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class FeedbackPort(Protocol):
    """Abstract interface for paper feedback operations."""

    def add_paper_feedback(
        self,
        *,
        user_id: str,
        track_id: int,
        paper_id: str,
        action: str,
        weight: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]: ...

    def list_paper_feedback(
        self,
        *,
        user_id: str,
        track_id: int,
        action: Optional[str] = None,
        limit: int = 200,
    ) -> List[Dict[str, Any]]: ...

    def list_paper_feedback_ids(
        self,
        *,
        user_id: str,
        track_id: int,
        action: str,
        limit: int = 500,
    ) -> set[str]: ...
