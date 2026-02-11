# src/paperbot/infrastructure/harvesters/__init__.py
"""
Paper harvesters for multiple academic sources.

Each harvester implements the HarvesterPort interface and normalizes
results to the HarvestedPaper format.
"""

from .arxiv_harvester import ArxivHarvester
from .semantic_scholar_harvester import SemanticScholarHarvester
from .openalex_harvester import OpenAlexHarvester

__all__ = [
    "ArxivHarvester",
    "SemanticScholarHarvester",
    "OpenAlexHarvester",
]
