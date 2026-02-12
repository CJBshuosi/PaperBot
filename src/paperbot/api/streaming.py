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
from typing import Any, AsyncGenerator, Dict, Optional
from uuid import uuid4


def _new_stream_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


@dataclass
class StreamEvent:
    """SSE event structure."""

    type: str  # progress, result, error, done
    data: Any = None
    message: Optional[str] = None
    envelope: Optional[Dict[str, Any]] = None

    def to_sse(self) -> str:
        """Convert to SSE format."""
        payload = {
            "type": self.type,
            "data": self.data,
            "message": self.message,
            "envelope": self.envelope,
        }
        return f"data: {json.dumps(payload)}\n\n"


def sse_done() -> str:
    """Return SSE done signal."""
    return "data: [DONE]\n\n"


def _with_envelope(
    event: StreamEvent,
    *,
    workflow: str,
    run_id: str,
    trace_id: str,
    seq: int,
) -> StreamEvent:
    if event.envelope:
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
