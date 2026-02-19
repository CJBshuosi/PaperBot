"""ResearchTrack domain aggregate root (extracted from research_store)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class ResearchTrack:
    """Research direction / track aggregate root."""

    id: Optional[int] = None
    user_id: str = ""
    name: str = ""
    description: str = ""
    keywords: List[str] = field(default_factory=list)
    venues: List[str] = field(default_factory=list)
    methods: List[str] = field(default_factory=list)
    is_active: bool = False
    archived_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
