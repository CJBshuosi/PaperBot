import { NextResponse } from "next/server"

import { apiBaseUrl } from "@/app/api/research/_base"

export async function GET(_req: Request, ctx: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await ctx.params
  const upstream = await fetch(
    `${apiBaseUrl()}/api/research/paperscool/sessions/${encodeURIComponent(sessionId)}`,
    { cache: "no-store" },
  )

  const body = await upstream.text()
  return new NextResponse(body, {
    status: upstream.status,
    headers: { "Content-Type": upstream.headers.get("content-type") || "application/json" },
  })
}
