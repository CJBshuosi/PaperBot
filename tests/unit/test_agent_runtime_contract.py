from __future__ import annotations

import pytest

from paperbot.core.abstractions import AgentRunContext, BaseAgentRuntime, LegacyMethodRuntime


class _EchoRuntime(BaseAgentRuntime[dict, dict]):
    async def plan(self, input_data: dict, *, context: AgentRunContext):
        return {"planned": True, "keys": sorted(input_data.keys())}

    async def execute(self, input_data: dict, *, context: AgentRunContext, plan: dict):
        return {"input": input_data, "plan": plan, "stage": context.stage}


class _LegacyAgent:
    def sync_method(self, value: int) -> int:
        return value + 1

    async def async_method(self, value: int) -> int:
        return value + 2


@pytest.mark.asyncio
async def test_base_agent_runtime_run_emits_events():
    runtime = _EchoRuntime()
    context = AgentRunContext(run_id="r1", trace_id="t1", workflow="wf", agent_name="Echo")

    events = []

    result = await runtime.run({"a": 1}, context=context, emit=events.append)

    assert result.ok is True
    assert result.output is not None
    assert result.output["stage"] == "execute"
    assert [e.kind for e in events] == ["input", "plan", "result", "finalize"]


@pytest.mark.asyncio
async def test_legacy_method_runtime_supports_sync_and_async_methods():
    legacy = _LegacyAgent()
    context = AgentRunContext(run_id="r2", trace_id="t2", workflow="wf", agent_name="Legacy")

    sync_runtime = LegacyMethodRuntime(agent=legacy, method_name="sync_method")
    sync_result = await sync_runtime.run(
        {"args": [3], "kwargs": {}},
        context=context,
    )
    assert sync_result.ok is True
    assert sync_result.output == 4

    async_runtime = LegacyMethodRuntime(agent=legacy, method_name="async_method")
    async_result = await async_runtime.run(
        {"args": [3], "kwargs": {}},
        context=context,
    )
    assert async_result.ok is True
    assert async_result.output == 5
