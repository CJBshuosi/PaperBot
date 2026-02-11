"""
QueryRewriter unit tests.
"""

import pytest

from paperbot.application.services.query_rewriter import QueryRewriter


class TestQueryRewriter:
    """QueryRewriter tests."""

    def setup_method(self):
        """Create fresh rewriter for each test."""
        self.rewriter = QueryRewriter()

    def test_rewrite_no_expansion(self):
        """Query without abbreviations returns single item."""
        queries = self.rewriter.rewrite("deep learning")
        assert queries == ["deep learning"]

    def test_rewrite_llm_expansion(self):
        """LLM expands to large language model."""
        queries = self.rewriter.rewrite("LLM security")
        assert len(queries) == 2
        assert "LLM security" in queries
        assert "large language model security" in queries

    def test_rewrite_multiple_abbreviations(self):
        """Multiple abbreviations are expanded."""
        queries = self.rewriter.rewrite("ML and NLP")
        assert len(queries) == 2
        assert "ML and NLP" in queries
        assert "machine learning and natural language processing" in queries

    def test_rewrite_case_insensitive(self):
        """Abbreviation matching is case-insensitive."""
        queries = self.rewriter.rewrite("llm")
        assert "large language model" in queries

        queries = self.rewriter.rewrite("LLM")
        assert "large language model" in queries

    def test_rewrite_punctuation_handled(self):
        """Punctuation doesn't prevent matching."""
        queries = self.rewriter.rewrite("What is LLM?")
        assert len(queries) == 2
        # The expanded version should have the expansion
        assert any("large language model" in q for q in queries)

    def test_expand_all_basic(self):
        """expand_all expands list of keywords."""
        expanded = self.rewriter.expand_all(["ML", "deep learning"])

        # Should include originals and expansions
        assert "ML" in expanded or "machine learning" in expanded
        assert "deep learning" in expanded

    def test_expand_all_deduplicates(self):
        """expand_all removes duplicate expansions."""
        # If both "ML" and "machine learning" are provided,
        # "machine learning" shouldn't appear twice
        expanded = self.rewriter.expand_all(["ML", "machine learning"])

        # Count occurrences of "machine learning" (normalized)
        ml_count = sum(1 for k in expanded if self.rewriter.normalize(k) == "machine learning")
        assert ml_count == 1

    def test_normalize_basic(self):
        """normalize applies standard transformations."""
        assert self.rewriter.normalize("Hello World") == "hello world"
        assert self.rewriter.normalize("  Multiple   Spaces  ") == "multiple spaces"
        assert self.rewriter.normalize("Special!@#Characters") == "special characters"

    def test_normalize_preserves_alphanumeric(self):
        """normalize preserves letters and numbers."""
        assert self.rewriter.normalize("GPT4 model") == "gpt4 model"
        assert self.rewriter.normalize("BERT-2022") == "bert 2022"

    def test_add_abbreviation(self):
        """Custom abbreviation can be added."""
        self.rewriter.add_abbreviation("XYZ", "extended yellow zebra")
        queries = self.rewriter.rewrite("XYZ test")
        assert "extended yellow zebra test" in queries

    def test_get_expansion(self):
        """get_expansion returns expansion for known abbreviations."""
        assert self.rewriter.get_expansion("llm") == "large language model"
        assert self.rewriter.get_expansion("LLM") == "large language model"
        assert self.rewriter.get_expansion("unknown") is None

    def test_default_abbreviations_exist(self):
        """Default abbreviations are available."""
        known_abbrevs = ["llm", "ml", "dl", "nlp", "cv", "rl", "gan", "cnn", "rnn", "bert", "gpt", "rag"]
        for abbrev in known_abbrevs:
            assert self.rewriter.get_expansion(abbrev) is not None

    def test_custom_abbreviations_override(self):
        """Custom abbreviations override defaults."""
        custom = {"llm": "custom large model"}
        rewriter = QueryRewriter(abbreviations=custom)

        assert rewriter.get_expansion("llm") == "custom large model"

    def test_empty_query_returns_empty(self):
        """Empty query returns single empty string."""
        queries = self.rewriter.rewrite("")
        assert queries == [""]

    def test_expand_all_empty_list(self):
        """Empty list returns empty result."""
        expanded = self.rewriter.expand_all([])
        assert expanded == []

    def test_rewrite_preserves_original(self):
        """Original query is always first in result."""
        queries = self.rewriter.rewrite("LLM for NLP")
        assert queries[0] == "LLM for NLP"

    def test_common_expansions(self):
        """Common AI/ML abbreviations expand correctly."""
        test_cases = [
            ("CNN", "convolutional neural network"),
            ("RNN", "recurrent neural network"),
            ("LSTM", "long short-term memory"),
            ("VAE", "variational autoencoder"),
            ("GAN", "generative adversarial network"),
            ("RL", "reinforcement learning"),
            ("RAG", "retrieval augmented generation"),
            ("NER", "named entity recognition"),
            ("QA", "question answering"),
        ]

        for abbrev, expected in test_cases:
            queries = self.rewriter.rewrite(abbrev)
            assert expected in queries, f"Expected '{expected}' in expansion of '{abbrev}'"
