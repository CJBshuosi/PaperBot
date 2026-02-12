"""Enrichment domain value objects."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class JudgeScore:
    """LLM-as-Judge evaluation result."""

    paper_id: int
    query: str
    overall: float = 0.0
    relevance: float = 0.0
    novelty: float = 0.0
    rigor: float = 0.0
    impact: float = 0.0
    clarity: float = 0.0
    recommendation: str = ""
    one_line_summary: str = ""
    judge_model: str = ""
    scored_at: Optional[datetime] = None


@dataclass(frozen=True)
class LLMSummary:
    """LLM-generated paper summary."""

    paper_id: int
    summary: str = ""
    key_contributions: str = ""
    model: str = ""
    generated_at: Optional[datetime] = None
