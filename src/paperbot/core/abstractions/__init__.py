"""
核心抽象：统一 Agent/Node 的执行契约与结果结构。
"""

from .agent_runtime import (
    AgentError,
    AgentMessage,
    AgentResult,
    AgentRunContext,
    AgentRuntime,
    BaseAgentRuntime,
    LegacyMethodRuntime,
)
from .executable import Executable, ExecutionResult, ensure_execution_result

__all__ = [
    "AgentRuntime",
    "AgentRunContext",
    "AgentMessage",
    "AgentResult",
    "AgentError",
    "BaseAgentRuntime",
    "LegacyMethodRuntime",
    "Executable",
    "ExecutionResult",
    "ensure_execution_result",
]
