"""
Unified runtime contract for agent-like execution.

This module introduces a stable lifecycle contract:
input -> plan -> execute -> emit events -> finalize

It is intentionally framework-agnostic and can wrap existing legacy agents.
"""

from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Generic, Optional, Protocol, TypeVar

TInput = TypeVar("TInput")
TOutput = TypeVar("TOutput")


@dataclass
class AgentRunContext:
    """Execution context propagated across routes/workflows/runtime."""

    run_id: str
    trace_id: str
    workflow: str
    agent_name: str = ""
    stage: str = "input"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def with_stage(self, stage: str) -> "AgentRunContext":
        return AgentRunContext(
            run_id=self.run_id,
            trace_id=self.trace_id,
            workflow=self.workflow,
            agent_name=self.agent_name,
            stage=stage,
            metadata=dict(self.metadata),
        )


@dataclass
class AgentMessage:
    """Unified runtime event payload."""

    kind: str
    context: AgentRunContext
    payload: Dict[str, Any] = field(default_factory=dict)
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "run_id": self.context.run_id,
            "trace_id": self.context.trace_id,
            "workflow": self.context.workflow,
            "agent_name": self.context.agent_name,
            "stage": self.context.stage,
            "payload": self.payload,
            "ts": self.ts,
        }


@dataclass
class AgentError(Exception):
    """Structured runtime error."""

    message: str
    code: str = "agent_runtime_error"
    retryable: bool = False
    details: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.message


@dataclass
class AgentResult(Generic[TOutput]):
    """Standardized runtime result."""

    ok: bool
    output: Optional[TOutput] = None
    error: Optional[AgentError] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def success(cls, output: TOutput, **metadata: Any) -> "AgentResult[TOutput]":
        return cls(ok=True, output=output, metadata=metadata or {})

    @classmethod
    def failure(
        cls,
        message: str,
        *,
        code: str = "agent_runtime_error",
        retryable: bool = False,
        details: Optional[Dict[str, Any]] = None,
        **metadata: Any,
    ) -> "AgentResult[TOutput]":
        return cls(
            ok=False,
            error=AgentError(
                message=message,
                code=code,
                retryable=retryable,
                details=details or {},
            ),
            metadata=metadata or {},
        )


EmitFn = Callable[[AgentMessage], None]


class AgentRuntime(Protocol, Generic[TInput, TOutput]):
    """Unified runtime protocol for all agent executors."""

    async def run(
        self,
        input_data: TInput,
        *,
        context: AgentRunContext,
        emit: Optional[EmitFn] = None,
    ) -> AgentResult[TOutput]: ...


class BaseAgentRuntime(ABC, Generic[TInput, TOutput]):
    """Template implementation for agent runtime lifecycle."""

    async def plan(
        self,
        input_data: TInput,
        *,
        context: AgentRunContext,
    ) -> Dict[str, Any]:
        return {}

    @abstractmethod
    async def execute(
        self,
        input_data: TInput,
        *,
        context: AgentRunContext,
        plan: Dict[str, Any],
    ) -> TOutput:
        raise NotImplementedError

    async def finalize(
        self,
        result: AgentResult[TOutput],
        *,
        context: AgentRunContext,
    ) -> AgentResult[TOutput]:
        return result

    async def run(
        self,
        input_data: TInput,
        *,
        context: AgentRunContext,
        emit: Optional[EmitFn] = None,
    ) -> AgentResult[TOutput]:
        def _emit(kind: str, stage: str, payload: Optional[Dict[str, Any]] = None) -> None:
            if emit is None:
                return
            emit(
                AgentMessage(
                    kind=kind,
                    context=context.with_stage(stage),
                    payload=payload or {},
                )
            )

        _emit("input", "input")

        try:
            plan = await self.plan(input_data, context=context.with_stage("plan"))
            _emit("plan", "plan", {"plan": plan})

            output = await self.execute(
                input_data,
                context=context.with_stage("execute"),
                plan=plan,
            )
            result = AgentResult.success(output)
            _emit("result", "result")
        except AgentError as exc:
            result = AgentResult(ok=False, error=exc)
            _emit("error", "error", {"message": exc.message, "code": exc.code})
        except Exception as exc:  # noqa: BLE001
            result = AgentResult.failure(str(exc))
            _emit("error", "error", {"message": str(exc), "code": "unhandled_exception"})

        finalized = await self.finalize(result, context=context.with_stage("finalize"))
        _emit("finalize", "finalize", {"ok": finalized.ok})
        return finalized


class LegacyMethodRuntime(BaseAgentRuntime[Dict[str, Any], Any]):
    """Compatibility adapter for existing agent methods.

    Expected input format:
    {
      "args": [...],
      "kwargs": {...}
    }
    """

    def __init__(self, *, agent: Any, method_name: str):
        self._agent = agent
        self._method_name = method_name

    async def execute(
        self,
        input_data: Dict[str, Any],
        *,
        context: AgentRunContext,
        plan: Dict[str, Any],
    ) -> Any:
        method = getattr(self._agent, self._method_name, None)
        if method is None:
            raise AgentError(
                message=f"method '{self._method_name}' not found on legacy agent",
                code="method_not_found",
            )

        args = input_data.get("args") if isinstance(input_data, dict) else None
        kwargs = input_data.get("kwargs") if isinstance(input_data, dict) else None
        args = args if isinstance(args, list) else []
        kwargs = kwargs if isinstance(kwargs, dict) else {}

        result = method(*args, **kwargs)
        if inspect.isawaitable(result):
            return await result
        return result
