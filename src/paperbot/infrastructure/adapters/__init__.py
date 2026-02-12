"""SearchPort adapter registry."""

from __future__ import annotations

from typing import Dict

from paperbot.application.ports.paper_search_port import SearchPort
from paperbot.infrastructure.adapters.arxiv_search_adapter import ArxivSearchAdapter
from paperbot.infrastructure.adapters.hf_daily_adapter import HFDailyAdapter
from paperbot.infrastructure.adapters.openalex_adapter import OpenAlexAdapter
from paperbot.infrastructure.adapters.paperscool_adapter import PapersCoolAdapter
from paperbot.infrastructure.adapters.s2_search_adapter import S2SearchAdapter


def build_adapter_registry() -> Dict[str, SearchPort]:
    return {
        "semantic_scholar": S2SearchAdapter(),
        "arxiv": ArxivSearchAdapter(),
        "papers_cool": PapersCoolAdapter(),
        "hf_daily": HFDailyAdapter(),
        "openalex": OpenAlexAdapter(),
    }
