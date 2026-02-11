export const runtime = "nodejs"

import { apiBaseUrl, proxyJson } from "../../research/_base"

export async function POST(req: Request) {
  return proxyJson(req, `${apiBaseUrl()}/api/newsletter/subscribe`, "POST")
}
