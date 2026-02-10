"""
VenueRecommender unit tests.
"""

import pytest

from paperbot.application.services.venue_recommender import VenueRecommender


class TestVenueRecommender:
    """VenueRecommender tests."""

    def setup_method(self):
        """Create fresh recommender for each test."""
        self.recommender = VenueRecommender()

    def test_recommend_security_keywords(self):
        """Security keywords recommend security venues."""
        venues = self.recommender.recommend(["ransomware"])

        assert len(venues) > 0
        # Should include top security venues
        security_venues = {"CCS", "S&P", "USENIX Security", "NDSS"}
        assert any(v in security_venues for v in venues)

    def test_recommend_ml_keywords(self):
        """ML keywords recommend ML venues."""
        venues = self.recommender.recommend(["machine learning"])

        assert len(venues) > 0
        ml_venues = {"NeurIPS", "ICML", "ICLR"}
        assert any(v in ml_venues for v in venues)

    def test_recommend_nlp_keywords(self):
        """NLP keywords recommend NLP venues."""
        venues = self.recommender.recommend(["natural language"])

        assert len(venues) > 0
        nlp_venues = {"ACL", "EMNLP", "NAACL"}
        assert any(v in nlp_venues for v in venues)

    def test_recommend_database_keywords(self):
        """Database keywords recommend database venues."""
        venues = self.recommender.recommend(["database", "sql"])

        assert len(venues) > 0
        db_venues = {"SIGMOD", "VLDB", "ICDE"}
        assert any(v in db_venues for v in venues)

    def test_recommend_systems_keywords(self):
        """Systems keywords recommend systems venues."""
        venues = self.recommender.recommend(["distributed systems"])

        assert len(venues) > 0
        sys_venues = {"OSDI", "SOSP", "EuroSys", "NSDI"}
        assert any(v in sys_venues for v in venues)

    def test_recommend_empty_keywords(self):
        """Empty keywords return empty result."""
        venues = self.recommender.recommend([])
        assert venues == []

    def test_recommend_unknown_keywords(self):
        """Unknown keywords return empty result."""
        venues = self.recommender.recommend(["xyznonexistent123"])
        assert venues == []

    def test_recommend_max_venues(self):
        """max_venues limits output count."""
        venues = self.recommender.recommend(["security", "machine learning"], max_venues=3)
        assert len(venues) <= 3

    def test_recommend_default_max_venues(self):
        """Default max_venues is 5."""
        venues = self.recommender.recommend(["security", "machine learning", "deep learning"])
        assert len(venues) <= 5

    def test_recommend_multiple_keywords_combined(self):
        """Multiple keywords combine scores."""
        # Single keyword
        venues_single = self.recommender.recommend(["security"])

        # Multiple related keywords should boost same venues
        venues_multi = self.recommender.recommend(["security", "malware", "ransomware"])

        # Both should return security venues at top
        assert len(venues_single) > 0
        assert len(venues_multi) > 0

    def test_recommend_case_insensitive(self):
        """Keyword matching is case-insensitive."""
        venues_lower = self.recommender.recommend(["security"])
        venues_upper = self.recommender.recommend(["SECURITY"])
        venues_mixed = self.recommender.recommend(["Security"])

        assert venues_lower == venues_upper == venues_mixed

    def test_recommend_partial_match(self):
        """Partial keyword matches contribute to scores."""
        # "learning" should partially match "machine learning", "deep learning", etc.
        venues = self.recommender.recommend(["learning"])
        assert len(venues) > 0

    def test_get_venues_for_domain(self):
        """get_venues_for_domain returns specific domain venues."""
        venues = self.recommender.get_venues_for_domain("security")
        assert "CCS" in venues
        assert "S&P" in venues

    def test_get_venues_for_unknown_domain(self):
        """Unknown domain returns empty list."""
        venues = self.recommender.get_venues_for_domain("unknown_domain_xyz")
        assert venues == []

    def test_add_mapping(self):
        """Custom mapping can be added."""
        self.recommender.add_mapping("custom_topic", ["Venue1", "Venue2"])
        venues = self.recommender.get_venues_for_domain("custom_topic")
        assert "Venue1" in venues
        assert "Venue2" in venues

    def test_add_mapping_updates_recommend(self):
        """Added mapping affects recommendations."""
        self.recommender.add_mapping("quantum", ["QIP", "Quantum"])
        venues = self.recommender.recommend(["quantum"])
        assert "QIP" in venues or "Quantum" in venues

    def test_custom_mappings_in_constructor(self):
        """Custom mappings can be passed in constructor."""
        custom = {"custom_key": ["CustomVenue1", "CustomVenue2"]}
        recommender = VenueRecommender(mappings=custom)

        venues = recommender.get_venues_for_domain("custom_key")
        assert "CustomVenue1" in venues
        assert "CustomVenue2" in venues

    def test_default_mappings_preserved_with_custom(self):
        """Default mappings are preserved when custom mappings are added."""
        custom = {"new_domain": ["NewVenue"]}
        recommender = VenueRecommender(mappings=custom)

        # Default mapping should still work
        security_venues = recommender.get_venues_for_domain("security")
        assert len(security_venues) > 0

        # Custom mapping should also work
        new_venues = recommender.get_venues_for_domain("new_domain")
        assert "NewVenue" in new_venues

    def test_recommend_sorted_by_relevance(self):
        """Venues are sorted by relevance score."""
        # Multiple keywords all pointing to security should rank security venues higher
        venues = self.recommender.recommend(
            ["security", "ransomware", "malware", "attack"]
        )

        # First venue should be a security venue
        if venues:
            security_venues = {"CCS", "S&P", "USENIX Security", "NDSS"}
            assert venues[0] in security_venues

    def test_recommend_whitespace_handling(self):
        """Keywords with extra whitespace are handled."""
        venues1 = self.recommender.recommend(["security"])
        venues2 = self.recommender.recommend(["  security  "])

        assert venues1 == venues2

    def test_recommend_empty_string_keyword(self):
        """Empty string keyword is ignored."""
        venues = self.recommender.recommend(["", "security", ""])
        assert len(venues) > 0
        # Should still recommend security venues
        security_venues = {"CCS", "S&P", "USENIX Security", "NDSS"}
        assert any(v in security_venues for v in venues)
