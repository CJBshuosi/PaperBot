import { apiBaseUrl, proxyJson } from "@/app/api/research/_base"

export const runtime = "nodejs"

export async function POST(req: Request, ctx: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await ctx.params
  return proxyJson(
    req,
    `${apiBaseUrl()}/api/research/paperscool/sessions/${encodeURIComponent(sessionId)}/approve`,
    "POST",
  )
}
