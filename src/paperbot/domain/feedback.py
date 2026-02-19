"""Feedback domain value objects."""

from __future__ import annotations

from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional


class FeedbackAction(str, Enum):
    LIKE = "like"
    DISLIKE = "dislike"
    SKIP = "skip"
    SAVE = "save"
    CITE = "cite"


@dataclass(frozen=True)
class PaperFeedback:
    """Immutable feedback event."""

    user_id: str
    track_id: int
    paper_id: str
    action: FeedbackAction
    weight: float = 0.0
    canonical_paper_id: Optional[int] = None
    ts: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
