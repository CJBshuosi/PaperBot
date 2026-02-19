"""
Streaming utilities for Server-Sent Events (SSE).

Provides a normalized envelope for stream observability:
- workflow
- run_id
- trace_id
- seq
- phase
- ts
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, AsyncGenerator, Dict, Optional
from uuid import uuid4


class StandardEvent(str, Enum):
    STATUS = "status"
    PROGRESS = "progress"
    TOOL = "tool"
    RESULT = "result"
    ERROR = "error"
    DONE = "done"


def _new_stream_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


@dataclass
class StreamEvent:
    """SSE event structure."""

    type: str  # progress, result, error, done
    event: Optional[str] = None  # canonical event kind for unified frontend handling
    data: Any = None
    message: Optional[str] = None
    envelope: Optional[Dict[str, Any]] = None

    def to_sse(self) -> str:
        """Convert to SSE format."""
        payload = {
            "type": self.type,
            "event": self.event,
            "data": self.data,
            "message": self.message,
            "envelope": self.envelope,
        }
        return f"data: {json.dumps(payload)}\n\n"


def sse_done() -> str:
    """Return SSE done signal."""
    return "data: [DONE]\n\n"


def _canonical_event_kind(
    *,
    event_type: str,
    data: Any,
    explicit_event: Optional[str],
) -> str:
    if explicit_event:
        return str(explicit_event)

    t = str(event_type or "").strip().lower()
    if t in {"error", "failed", "failure"}:
        return StandardEvent.ERROR.value
    if t in {"result", "final", "final_result"}:
        return StandardEvent.RESULT.value
    if t in {"done", "completed", "complete"}:
        return StandardEvent.DONE.value
    if t == "status":
        return StandardEvent.STATUS.value
    if t.startswith("tool"):
        return StandardEvent.TOOL.value
    if t in {
        "progress",
        "search_done",
        "report_built",
        "llm_summary",
        "llm_done",
        "trend",
        "insight",
        "judge",
        "judge_done",
        "filter_done",
    }:
        return StandardEvent.PROGRESS.value

    if isinstance(data, dict):
        if any(k in data for k in ("phase", "delta", "done", "total")):
            return StandardEvent.PROGRESS.value
    return StandardEvent.STATUS.value


def _with_envelope(
    event: StreamEvent,
    *,
    workflow: str,
    run_id: str,
    trace_id: str,
    seq: int,
) -> StreamEvent:
    canonical_event = _canonical_event_kind(
        event_type=event.type,
        data=event.data,
        explicit_event=event.event,
    )
    event.event = canonical_event

    if event.envelope:
        if "event" not in event.envelope:
            event.envelope["event"] = canonical_event
        return event

    phase = None
    if isinstance(event.data, dict):
        phase = event.data.get("phase")

    event.envelope = {
        "workflow": workflow or "unknown",
        "run_id": run_id,
        "trace_id": trace_id,
        "seq": seq,
        "phase": phase,
        "event": canonical_event,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    return event


async def wrap_generator(
    generator: AsyncGenerator[StreamEvent, None],
    *,
    workflow: str = "",
    run_id: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """Wrap a StreamEvent generator to SSE strings with a normalized envelope."""
    resolved_run_id = run_id or _new_stream_id("run")
    resolved_trace_id = trace_id or _new_stream_id("trace")
    seq = 0

    try:
        async for event in generator:
            seq += 1
            yield _with_envelope(
                event,
                workflow=workflow,
                run_id=resolved_run_id,
                trace_id=resolved_trace_id,
                seq=seq,
            ).to_sse()
        yield sse_done()
    except Exception as e:
        seq += 1
        yield _with_envelope(
            StreamEvent(type="error", message=str(e)),
            workflow=workflow,
            run_id=resolved_run_id,
            trace_id=resolved_trace_id,
            seq=seq,
        ).to_sse()
        yield sse_done()
