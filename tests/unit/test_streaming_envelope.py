from __future__ import annotations

import json

import pytest

from paperbot.api.streaming import StreamEvent, wrap_generator


async def _simple_stream():
    yield StreamEvent(type="progress", data={"phase": "judge", "message": "running"})
    yield StreamEvent(type="search_done", data={"ok": True})
    yield StreamEvent(type="result", data={"ok": True})


@pytest.mark.asyncio
async def test_wrap_generator_injects_envelope():
    payloads = []
    async for raw in wrap_generator(
        _simple_stream(),
        workflow="paperscool_analyze",
        run_id="run_x",
        trace_id="trace_x",
    ):
        if not raw.startswith("data: "):
            continue
        data = raw.removeprefix("data: ").strip()
        if data == "[DONE]":
            continue
        payloads.append(json.loads(data))

    assert len(payloads) == 3
    for idx, payload in enumerate(payloads, start=1):
        env = payload["envelope"]
        assert env["workflow"] == "paperscool_analyze"
        assert env["run_id"] == "run_x"
        assert env["trace_id"] == "trace_x"
        assert env["seq"] == idx
        assert isinstance(env["ts"], str)
        assert env["event"] in {"progress", "result"}

    assert payloads[0]["envelope"]["phase"] == "judge"
    assert payloads[0]["event"] == "progress"
    assert payloads[1]["event"] == "progress"
    assert payloads[2]["event"] == "result"
