"use client"

import { useMemo, useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"

type DiscoveryPaper = {
  id?: number
  title?: string
  abstract?: string
  authors?: string[]
  year?: number
  venue?: string
  citation_count?: number
  url?: string
  doi?: string
  arxiv_id?: string
  semantic_scholar_id?: string
  openalex_id?: string
  source?: string
}

type DiscoveryItem = {
  candidate_key?: string
  paper: DiscoveryPaper
  edge_types: string[]
  score: number
  why_this_paper: string[]
}

type DiscoveryResponse = {
  seed: { seed_type?: string; seed_id?: string; title?: string; name?: string }
  nodes: Array<{ id: string; label: string; type: string; year?: number; score?: number }>
  edges: Array<{ source: string; target: string; type: string; weight?: number }>
  items: DiscoveryItem[]
  stats?: Record<string, unknown>
}

type SavePaperPayload = {
  paper_id: string
  title: string
  abstract?: string
  authors?: string[]
  year?: number
  venue?: string
  citation_count?: number
  url?: string
  source?: string
}

const EDGE_COLORS: Record<string, string> = {
  related: "#3b82f6",
  cited: "#10b981",
  citing: "#f59e0b",
  coauthor: "#8b5cf6",
}

function toSavePayload(item: DiscoveryItem): SavePaperPayload | null {
  const paper = item.paper || {}
  const title = String(paper.title || "").trim()
  if (!title) return null
  const paperId =
    String(paper.semantic_scholar_id || "").trim() ||
    String(paper.openalex_id || "").trim() ||
    String(paper.arxiv_id || "").trim() ||
    String(paper.doi || "").trim() ||
    `title:${title}`
  return {
    paper_id: paperId,
    title,
    abstract: paper.abstract || "",
    authors: paper.authors || [],
    year: paper.year,
    venue: paper.venue,
    citation_count: paper.citation_count || 0,
    url: paper.url || "",
    source: paper.source || "semantic_scholar",
  }
}

interface DiscoveryGraphWorkspaceProps {
  userId: string
  trackId: number | null
  onSavePaper: (paper: SavePaperPayload) => Promise<void>
}

export default function DiscoveryGraphWorkspace({
  userId,
  trackId,
  onSavePaper,
}: DiscoveryGraphWorkspaceProps) {
  const [seedType, setSeedType] = useState<"doi" | "arxiv" | "openalex" | "semantic_scholar" | "author">("doi")
  const [seedId, setSeedId] = useState("")
  const [limit, setLimit] = useState("30")
  const [edgeFilter, setEdgeFilter] = useState<Record<string, boolean>>({
    related: true,
    cited: true,
    citing: true,
    coauthor: true,
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [payload, setPayload] = useState<DiscoveryResponse | null>(null)
  const [savingKey, setSavingKey] = useState<string | null>(null)

  const filteredItems = useMemo(() => {
    const items = payload?.items || []
    return items.filter((item) => (item.edge_types || []).some((edge) => edgeFilter[edge]))
  }, [payload, edgeFilter])

  const filteredNodeIds = useMemo(() => {
    const rows = new Set<string>()
    for (const item of filteredItems) {
      const key = String(item.candidate_key || "").trim()
      if (key) rows.add(key)
    }
    return rows
  }, [filteredItems])

  const displayEdges = useMemo(() => {
    const edges = payload?.edges || []
    return edges.filter((edge) => edgeFilter[edge.type] && (filteredNodeIds.size === 0 || filteredNodeIds.has(edge.target)))
  }, [payload, edgeFilter, filteredNodeIds])

  const graphPoints = useMemo(() => {
    const nodes = payload?.nodes || []
    const seed = nodes.find((node) => node.type === "seed")
    const papers = nodes.filter((node) => node.type === "paper" && filteredNodeIds.has(node.id))
    const center = { x: 220, y: 150 }
    const radius = 110
    const map: Record<string, { x: number; y: number; label: string; type: string }> = {}
    if (seed) map[seed.id] = { x: center.x, y: center.y, label: seed.label, type: "seed" }
    papers.forEach((node, index) => {
      const angle = (index / Math.max(papers.length, 1)) * Math.PI * 2
      map[node.id] = {
        x: center.x + Math.cos(angle) * radius,
        y: center.y + Math.sin(angle) * radius,
        label: node.label,
        type: "paper",
      }
    })
    return map
  }, [payload, filteredNodeIds])

  async function runDiscovery() {
    if (!seedId.trim()) return
    setLoading(true)
    setError(null)
    try {
      const parsedLimit = Number(limit) || 30
      const res = await fetch("/api/research/discovery/seed", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          track_id: trackId ?? undefined,
          seed_type: seedType,
          seed_id: seedId.trim(),
          limit: Math.max(1, Math.min(parsedLimit, 200)),
          include_related: true,
          include_cited: true,
          include_citing: true,
          include_coauthor: true,
          personalized: true,
        }),
      })
      if (!res.ok) {
        const detail = await res.text()
        throw new Error(detail || `HTTP ${res.status}`)
      }
      setPayload((await res.json()) as DiscoveryResponse)
    } catch (err) {
      const detail = err instanceof Error ? err.message : String(err)
      setError(detail)
      setPayload(null)
    } finally {
      setLoading(false)
    }
  }

  async function handleSave(item: DiscoveryItem) {
    const savePayload = toSavePayload(item)
    if (!savePayload) return
    setSavingKey(savePayload.paper_id)
    try {
      await onSavePaper(savePayload)
    } finally {
      setSavingKey(null)
    }
  }

  return (
    <Card className="mt-6">
      <CardHeader>
        <CardTitle>Discovery Graph</CardTitle>
        <CardDescription>Seed paper/author expansion with graph + explainable ranking.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-2 md:grid-cols-4">
          <select
            className="h-9 rounded-md border bg-background px-2 text-sm"
            value={seedType}
            onChange={(event) => setSeedType(event.target.value as typeof seedType)}
            disabled={loading}
          >
            <option value="doi">DOI</option>
            <option value="arxiv">arXiv</option>
            <option value="openalex">OpenAlex</option>
            <option value="semantic_scholar">Semantic Scholar</option>
            <option value="author">Author ID</option>
          </select>
          <Input
            value={seedId}
            onChange={(event) => setSeedId(event.target.value)}
            placeholder="Seed identifier"
            disabled={loading}
            className="md:col-span-2"
          />
          <div className="flex items-center gap-2">
            <Input
              value={limit}
              onChange={(event) => setLimit(event.target.value)}
              placeholder="30"
              disabled={loading}
            />
            <Button onClick={runDiscovery} disabled={loading || !seedId.trim()}>
              {loading ? "Discovering..." : "Discover"}
            </Button>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {Object.keys(edgeFilter).map((edge) => (
            <label key={edge} className="flex items-center gap-2 text-sm">
              <Checkbox
                checked={edgeFilter[edge]}
                onCheckedChange={(checked) =>
                  setEdgeFilter((prev) => ({ ...prev, [edge]: Boolean(checked) }))
                }
              />
              <span className="capitalize">{edge}</span>
            </label>
          ))}
          {payload?.stats ? (
            <Badge variant="outline">Candidates: {String(payload.stats.candidate_count || 0)}</Badge>
          ) : null}
        </div>

        {error ? <p className="text-sm text-destructive">{error}</p> : null}

        {!!payload && (
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-md border bg-muted/30 p-2">
              <svg viewBox="0 0 440 300" className="h-[300px] w-full">
                {displayEdges.map((edge, idx) => {
                  const from = graphPoints[edge.source]
                  const to = graphPoints[edge.target]
                  if (!from || !to) return null
                  return (
                    <line
                      key={`${edge.source}-${edge.target}-${idx}`}
                      x1={from.x}
                      y1={from.y}
                      x2={to.x}
                      y2={to.y}
                      stroke={EDGE_COLORS[edge.type] || "#94a3b8"}
                      strokeWidth={Math.max(1, Number(edge.weight || 1))}
                      opacity={0.8}
                    />
                  )
                })}
                {Object.entries(graphPoints).map(([id, node]) => (
                  <g key={id}>
                    <circle
                      cx={node.x}
                      cy={node.y}
                      r={node.type === "seed" ? 12 : 8}
                      fill={node.type === "seed" ? "#111827" : "#2563eb"}
                    />
                    <text
                      x={node.x}
                      y={node.y + (node.type === "seed" ? -16 : -12)}
                      textAnchor="middle"
                      fontSize="10"
                      fill="#334155"
                    >
                      {node.label.slice(0, 20)}
                    </text>
                  </g>
                ))}
              </svg>
            </div>

            <div className="space-y-2">
              {filteredItems.slice(0, 12).map((item, idx) => {
                const paper = item.paper || {}
                const savePayload = toSavePayload(item)
                const saveKey = savePayload?.paper_id || `${idx}`
                return (
                  <div key={`${saveKey}-${idx}`} className="rounded-md border p-3">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <p className="font-medium text-sm">{paper.title || "Untitled"}</p>
                        <p className="text-xs text-muted-foreground">
                          {(paper.authors || []).slice(0, 3).join(", ") || "Unknown authors"}
                        </p>
                        <div className="mt-1 flex flex-wrap gap-1">
                          {(item.edge_types || []).map((edge) => (
                            <Badge key={edge} variant="secondary">{edge}</Badge>
                          ))}
                          <Badge variant="outline">score {item.score.toFixed(2)}</Badge>
                        </div>
                        {(item.why_this_paper || []).length > 0 ? (
                          <p className="mt-1 text-xs text-muted-foreground">
                            {item.why_this_paper.join(" · ")}
                          </p>
                        ) : null}
                      </div>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleSave(item)}
                        disabled={!savePayload || savingKey === saveKey}
                      >
                        {savingKey === saveKey ? "Saving..." : "Save"}
                      </Button>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
