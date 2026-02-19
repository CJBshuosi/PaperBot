export const runtime = "nodejs"

import { apiBaseUrl, proxyJson } from "@/app/api/research/_base"

export async function POST(req: Request) {
  return proxyJson(
    req,
    `${apiBaseUrl()}/api/research/papers/related-work`,
    "POST",
  )
}
