import { apiBaseUrl, proxyJson } from "../../../research/_base"

export async function DELETE(
  req: Request,
  { params }: { params: Promise<{ paperId: string }> }
) {
  const { paperId } = await params
  const url = new URL(req.url)
  const upstream = `${apiBaseUrl()}/api/papers/${paperId}/save${url.search}`
  return proxyJson(req, upstream, "DELETE")
}

export async function POST(
  req: Request,
  { params }: { params: Promise<{ paperId: string }> }
) {
  const { paperId } = await params
  const upstream = `${apiBaseUrl()}/api/papers/${paperId}/save`
  return proxyJson(req, upstream, "POST")
}
