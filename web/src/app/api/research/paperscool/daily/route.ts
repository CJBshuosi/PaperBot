export const runtime = "nodejs"

import { apiBaseUrl } from "../../_base"

export async function POST(req: Request) {
  const body = await req.text()
  const contentType = req.headers.get("content-type") || "application/json"

  let upstream: Response
  try {
    upstream = await fetch(`${apiBaseUrl()}/api/research/paperscool/daily`, {
      method: "POST",
      headers: {
        "Content-Type": contentType,
        Accept: "text/event-stream, application/json",
      },
      body,
    })
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error)
    return Response.json(
      { detail: "Upstream API unreachable", error: detail },
      { status: 502 },
    )
  }

  const upstreamContentType = upstream.headers.get("content-type") || ""

  // SSE stream path — pipe through without buffering
  if (upstreamContentType.includes("text/event-stream")) {
    return new Response(upstream.body, {
      status: upstream.status,
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      },
    })
  }

  // JSON fallback (fast path when no LLM/Judge)
  const text = await upstream.text()
  return new Response(text, {
    status: upstream.status,
    headers: {
      "Content-Type": upstreamContentType || "application/json",
      "Cache-Control": "no-cache",
    },
  })
}
