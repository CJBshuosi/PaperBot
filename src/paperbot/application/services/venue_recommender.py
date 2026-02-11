# src/paperbot/application/services/venue_recommender.py
"""
Venue recommendation service.

Recommends relevant academic venues based on search keywords.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class VenueRecommender:
    """
    Recommend relevant venues based on keywords.

    Uses a static mapping from keywords/domains to top venues.
    Configuration can be loaded from config file or use defaults.
    """

    # Default keyword→venue mappings
    DEFAULT_MAPPINGS: Dict[str, List[str]] = {
        # Security
        "security": ["CCS", "S&P", "USENIX Security", "NDSS"],
        "ransomware": ["CCS", "S&P", "USENIX Security", "NDSS"],
        "malware": ["CCS", "S&P", "USENIX Security", "NDSS"],
        "cryptography": ["CRYPTO", "EUROCRYPT", "CCS"],
        "privacy": ["S&P", "PETS", "CCS", "USENIX Security"],
        "vulnerability": ["CCS", "S&P", "USENIX Security", "NDSS"],
        "attack": ["CCS", "S&P", "USENIX Security", "NDSS"],
        "adversarial": ["CCS", "S&P", "NeurIPS", "ICML"],
        # ML/AI
        "machine learning": ["NeurIPS", "ICML", "ICLR"],
        "deep learning": ["NeurIPS", "ICML", "ICLR", "CVPR"],
        "llm": ["NeurIPS", "ICML", "ACL", "EMNLP"],
        "large language model": ["NeurIPS", "ICML", "ACL", "EMNLP"],
        "transformer": ["NeurIPS", "ICML", "ACL", "EMNLP"],
        "gpt": ["NeurIPS", "ICML", "ACL", "EMNLP"],
        "nlp": ["ACL", "EMNLP", "NAACL", "NeurIPS"],
        "natural language": ["ACL", "EMNLP", "NAACL"],
        "computer vision": ["CVPR", "ICCV", "ECCV", "NeurIPS"],
        "image": ["CVPR", "ICCV", "ECCV"],
        "neural network": ["NeurIPS", "ICML", "ICLR"],
        "reinforcement learning": ["NeurIPS", "ICML", "ICLR"],
        "generative": ["NeurIPS", "ICML", "ICLR", "CVPR"],
        "diffusion": ["NeurIPS", "ICML", "ICLR", "CVPR"],
        # Systems
        "database": ["SIGMOD", "VLDB", "ICDE"],
        "query": ["SIGMOD", "VLDB", "ICDE"],
        "sql": ["SIGMOD", "VLDB", "ICDE"],
        "systems": ["OSDI", "SOSP", "EuroSys", "ATC"],
        "operating system": ["OSDI", "SOSP", "EuroSys"],
        "distributed": ["OSDI", "SOSP", "EuroSys", "NSDI"],
        "networking": ["SIGCOMM", "NSDI", "MobiCom"],
        "network": ["SIGCOMM", "NSDI", "MobiCom"],
        "cloud": ["OSDI", "SOSP", "EuroSys", "SoCC"],
        # Software Engineering
        "software engineering": ["ICSE", "FSE", "ASE"],
        "software": ["ICSE", "FSE", "ASE"],
        "testing": ["ICSE", "ISSTA", "FSE"],
        "bug": ["ICSE", "FSE", "ASE", "ISSTA"],
        "program analysis": ["PLDI", "POPL", "OOPSLA"],
        "compiler": ["PLDI", "CGO", "CC"],
        "verification": ["CAV", "PLDI", "POPL"],
        # HCI
        "hci": ["CHI", "UIST", "UbiComp"],
        "human computer": ["CHI", "UIST", "UbiComp"],
        "interaction": ["CHI", "UIST"],
        "user interface": ["CHI", "UIST"],
        # Data Mining
        "data mining": ["KDD", "ICDM", "WWW"],
        "knowledge graph": ["KDD", "WWW", "EMNLP"],
        "recommendation": ["KDD", "RecSys", "WWW"],
        # Robotics
        "robotics": ["ICRA", "IROS", "RSS"],
        "robot": ["ICRA", "IROS", "RSS"],
        "autonomous": ["ICRA", "IROS", "CVPR"],
    }

    def __init__(
        self,
        config_path: Optional[str] = None,
        mappings: Optional[Dict[str, List[str]]] = None,
    ):
        self.mappings = self.DEFAULT_MAPPINGS.copy()
        if mappings:
            self.mappings.update(mappings)
        if config_path:
            self._load_config(config_path)

    def _load_config(self, config_path: str) -> None:
        """Load venue mappings from YAML config file."""
        try:
            import yaml

            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            if config and isinstance(config, dict):
                venue_mappings = config.get("venue_mappings", {})
                if isinstance(venue_mappings, dict):
                    self.mappings.update(venue_mappings)
                    logger.info(f"Loaded {len(venue_mappings)} venue mappings from {config_path}")
        except Exception as e:
            logger.warning(f"Failed to load venue config from {config_path}: {e}")

    def recommend(
        self,
        keywords: List[str],
        *,
        max_venues: int = 5,
    ) -> List[str]:
        """
        Recommend venues based on keywords.

        Args:
            keywords: List of search keywords
            max_venues: Maximum number of venues to recommend

        Returns:
            List of recommended venue names, ordered by relevance
        """
        venue_scores: Dict[str, int] = {}

        for keyword in keywords:
            keyword_lower = keyword.lower().strip()
            if not keyword_lower:
                continue

            # Exact match (highest priority)
            if keyword_lower in self.mappings:
                for venue in self.mappings[keyword_lower]:
                    venue_scores[venue] = venue_scores.get(venue, 0) + 3

            # Partial match (medium priority)
            for mapped_kw, venues in self.mappings.items():
                if keyword_lower in mapped_kw or mapped_kw in keyword_lower:
                    for venue in venues:
                        venue_scores[venue] = venue_scores.get(venue, 0) + 1

        # Sort by score descending
        sorted_venues = sorted(venue_scores.items(), key=lambda x: -x[1])
        result = [v[0] for v in sorted_venues[:max_venues]]

        logger.debug(f"Recommended venues for {keywords}: {result}")
        return result

    def get_venues_for_domain(self, domain: str) -> List[str]:
        """Get venues for a specific domain keyword."""
        return self.mappings.get(domain.lower(), [])

    def add_mapping(self, keyword: str, venues: List[str]) -> None:
        """Add or update a keyword→venues mapping."""
        self.mappings[keyword.lower()] = venues
