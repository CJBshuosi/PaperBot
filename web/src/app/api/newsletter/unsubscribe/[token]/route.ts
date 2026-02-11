export const runtime = "nodejs"

import { apiBaseUrl } from "../../../research/_base"

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ token: string }> },
) {
  const { token } = await params
  try {
    const upstream = await fetch(
      `${apiBaseUrl()}/api/newsletter/unsubscribe/${encodeURIComponent(token)}`,
    )
    const text = await upstream.text()
    return new Response(text, {
      status: upstream.status,
      headers: {
        "Content-Type": upstream.headers.get("content-type") || "text/html",
      },
    })
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error)
    return new Response(
      `<html><body><h2>Error</h2><p>${detail}</p></body></html>`,
      { status: 502, headers: { "Content-Type": "text/html" } },
    )
  }
}
