# src/paperbot/application/services/query_rewriter.py
"""
Query rewriting service.

Expands and rewrites search queries for better coverage.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class QueryRewriter:
    """
    Expand and rewrite queries for better search coverage.

    Handles:
    - Abbreviation expansion (LLM → large language model)
    - Synonym addition
    - Query normalization
    """

    # Abbreviation → full form mappings
    DEFAULT_ABBREVIATIONS: Dict[str, str] = {
        "llm": "large language model",
        "llms": "large language models",
        "ml": "machine learning",
        "dl": "deep learning",
        "nlp": "natural language processing",
        "cv": "computer vision",
        "rl": "reinforcement learning",
        "gan": "generative adversarial network",
        "gans": "generative adversarial networks",
        "cnn": "convolutional neural network",
        "cnns": "convolutional neural networks",
        "rnn": "recurrent neural network",
        "rnns": "recurrent neural networks",
        "lstm": "long short-term memory",
        "bert": "bidirectional encoder representations from transformers",
        "gpt": "generative pre-trained transformer",
        "rag": "retrieval augmented generation",
        "vae": "variational autoencoder",
        "asr": "automatic speech recognition",
        "tts": "text to speech",
        "ocr": "optical character recognition",
        "sql": "structured query language",
        "api": "application programming interface",
        "ai": "artificial intelligence",
        "nn": "neural network",
        "dnn": "deep neural network",
        "mlp": "multilayer perceptron",
        "svm": "support vector machine",
        "knn": "k-nearest neighbors",
        "pca": "principal component analysis",
        "ssl": "self-supervised learning",
        "ner": "named entity recognition",
        "qa": "question answering",
        "ir": "information retrieval",
        "kg": "knowledge graph",
        "gcn": "graph convolutional network",
        "gnn": "graph neural network",
        "vit": "vision transformer",
        "clip": "contrastive language-image pre-training",
    }

    def __init__(self, abbreviations: Optional[Dict[str, str]] = None):
        self.abbreviations = {**self.DEFAULT_ABBREVIATIONS}
        if abbreviations:
            self.abbreviations.update(abbreviations)

    def rewrite(self, query: str) -> List[str]:
        """
        Rewrite query to produce expanded variations.

        Args:
            query: Original search query

        Returns:
            List of query variations (original + expanded)
        """
        queries = [query]

        # Tokenize and expand abbreviations
        words = query.lower().split()
        expanded_words = []
        has_expansion = False

        for word in words:
            # Remove punctuation for matching
            clean_word = re.sub(r"[^\w]", "", word)

            if clean_word in self.abbreviations:
                expanded_words.append(self.abbreviations[clean_word])
                has_expansion = True
            else:
                expanded_words.append(word)

        if has_expansion:
            expanded_query = " ".join(expanded_words)
            if expanded_query != query.lower():
                queries.append(expanded_query)

        logger.debug(f"Query rewrite: '{query}' → {queries}")
        return queries

    def expand_all(self, keywords: List[str]) -> List[str]:
        """
        Expand all keywords, returning unique expanded terms.

        Args:
            keywords: List of search keywords

        Returns:
            List of unique expanded keywords
        """
        expanded: List[str] = []
        seen: set[str] = set()

        for keyword in keywords:
            for variation in self.rewrite(keyword):
                normalized = self.normalize(variation)
                if normalized and normalized not in seen:
                    seen.add(normalized)
                    expanded.append(variation)

        return expanded

    def normalize(self, query: str) -> str:
        """
        Normalize query for consistent matching.

        - Lowercase
        - Remove extra whitespace
        - Remove special characters (except alphanumeric and space)
        """
        normalized = query.lower()
        normalized = re.sub(r"[^\w\s]", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    def add_abbreviation(self, abbrev: str, expansion: str) -> None:
        """Add or update an abbreviation mapping."""
        self.abbreviations[abbrev.lower()] = expansion.lower()

    def get_expansion(self, abbrev: str) -> Optional[str]:
        """Get the expansion for an abbreviation, if any."""
        return self.abbreviations.get(abbrev.lower())
