export const runtime = "nodejs"

import { Agent } from "undici"

import { apiBaseUrl } from "../../_base"

// Analyze can stream for a long time; disable body timeout on the proxy hop.
const sseDispatcher = new Agent({
  bodyTimeout: 0,
  headersTimeout: 0,
})

export async function POST(req: Request) {
  const body = await req.text()
  let upstream: Response
  try {
    upstream = await fetch(`${apiBaseUrl()}/api/research/paperscool/analyze`, {
      method: "POST",
      headers: {
        "Content-Type": req.headers.get("content-type") || "application/json",
        Accept: "text/event-stream",
      },
      body,
      dispatcher: sseDispatcher,
    } as RequestInit & { dispatcher: Agent })
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error)
    return Response.json(
      { detail: "Upstream API unreachable", error: detail },
      { status: 502 },
    )
  }

  const headers = new Headers()
  headers.set("Content-Type", upstream.headers.get("content-type") || "text/event-stream")
  headers.set("Cache-Control", "no-cache")
  headers.set("Connection", "keep-alive")

  return new Response(upstream.body, {
    status: upstream.status,
    headers,
  })
}
