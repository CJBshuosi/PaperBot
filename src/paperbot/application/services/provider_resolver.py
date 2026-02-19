from __future__ import annotations

from typing import Protocol

from paperbot.infrastructure.llm.providers.base import LLMProvider
from paperbot.infrastructure.llm.router import ModelRouter


class ProviderResolver(Protocol):
    """Resolve task_type -> provider instance."""

    def get_provider(self, task_type: str = "default") -> LLMProvider: ...


class RouterBackedProviderResolver:
    """Adapter that keeps existing ModelRouter behavior behind a resolver interface."""

    def __init__(self, router: ModelRouter):
        self._router = router

    def get_provider(self, task_type: str = "default") -> LLMProvider:
        return self._router.get_provider(task_type)
