export type StreamEnvelope = {
  workflow?: string
  run_id?: string
  trace_id?: string
  seq?: number
  phase?: string | null
  ts?: string
}

export type SSEMessage = {
  type?: string
  data?: unknown
  message?: string | null
  envelope?: StreamEnvelope | null
}

export type NormalizedSSEEvent = {
  type: string
  data: unknown
  message: string | null
  envelope: StreamEnvelope
}

function asEnvelope(raw: unknown): StreamEnvelope {
  if (!raw || typeof raw !== "object") return {}
  const obj = raw as Record<string, unknown>
  return {
    workflow: typeof obj.workflow === "string" ? obj.workflow : undefined,
    run_id: typeof obj.run_id === "string" ? obj.run_id : undefined,
    trace_id: typeof obj.trace_id === "string" ? obj.trace_id : undefined,
    seq: typeof obj.seq === "number" ? obj.seq : undefined,
    phase: typeof obj.phase === "string" ? obj.phase : null,
    ts: typeof obj.ts === "string" ? obj.ts : undefined,
  }
}

export function normalizeSSEMessage(message: SSEMessage, fallbackWorkflow = "unknown"): NormalizedSSEEvent {
  const dataObj = message.data && typeof message.data === "object" ? (message.data as Record<string, unknown>) : null
  const envelope = asEnvelope(message.envelope)
  const derivedPhase = typeof dataObj?.phase === "string" ? dataObj.phase : envelope.phase || null

  return {
    type: typeof message.type === "string" && message.type.length > 0 ? message.type : "unknown",
    data: message.data,
    message: typeof message.message === "string" ? message.message : null,
    envelope: {
      workflow: envelope.workflow || fallbackWorkflow,
      run_id: envelope.run_id,
      trace_id: envelope.trace_id,
      seq: envelope.seq,
      phase: derivedPhase,
      ts: envelope.ts,
    },
  }
}

export async function* readSSE(stream: ReadableStream<Uint8Array>): AsyncGenerator<SSEMessage> {
  const reader = stream.getReader()
  const decoder = new TextDecoder("utf-8")
  let buffer = ""

  while (true) {
    const { value, done } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })

    while (true) {
      const delimiterIndex = buffer.indexOf("\n\n")
      if (delimiterIndex === -1) break

      const rawEvent = buffer.slice(0, delimiterIndex)
      buffer = buffer.slice(delimiterIndex + 2)

      const lines = rawEvent.split("\n")
      for (const line of lines) {
        if (!line.startsWith("data:")) continue
        const payload = line.slice(5).trim()
        if (payload === "[DONE]") return
        try {
          yield JSON.parse(payload) as SSEMessage
        } catch {
          yield { type: "error", message: "Invalid SSE payload" }
        }
      }
    }
  }
}
