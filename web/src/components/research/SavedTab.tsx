"use client"

import { useEffect, useMemo, useState } from "react"
import { Loader2, RefreshCw } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"

import { PaperCard, type Paper } from "./PaperCard"

type SavedItem = {
  paper: {
    id?: number
    title?: string
    abstract?: string
    authors?: string[]
    year?: number
    venue?: string
    citation_count?: number
    url?: string
  }
  latest_judge?: Paper["latest_judge"]
  saved_at?: string | null
}

type SavedResponse = {
  user_id: string
  items: SavedItem[]
}

interface SavedTabProps {
  userId: string
  trackId: number | null
}

function toPaper(item: SavedItem): Paper {
  return {
    paper_id: String(item.paper.id || ""),
    title: item.paper.title || "Untitled",
    abstract: item.paper.abstract || "",
    authors: item.paper.authors || [],
    year: item.paper.year,
    venue: item.paper.venue,
    citation_count: item.paper.citation_count || 0,
    url: item.paper.url,
    latest_judge: item.latest_judge,
    is_saved: true,
  }
}

export function SavedTab({ userId, trackId }: SavedTabProps) {
  const [items, setItems] = useState<SavedItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const papers = useMemo(() => items.map(toPaper), [items])

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const qs = new URLSearchParams({
        user_id: userId,
        sort_by: "saved_at",
        limit: "100",
      })
      if (trackId) {
        qs.set("track_id", String(trackId))
      }
      const res = await fetch(`/api/research/papers/saved?${qs.toString()}`)
      if (!res.ok) {
        throw new Error(`${res.status} ${res.statusText}`)
      }
      const payload = (await res.json()) as SavedResponse
      setItems(payload.items || [])
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setItems([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load().catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId, trackId])

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">Saved papers scoped to current track.</p>
        <Button variant="outline" size="sm" onClick={() => load().catch(() => {})} disabled={loading}>
          {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
          Refresh
        </Button>
      </div>

      {error && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="py-3 text-sm text-red-700">{error}</CardContent>
        </Card>
      )}

      {loading && !papers.length ? (
        <div className="py-8 text-sm text-muted-foreground">Loading saved papers...</div>
      ) : !papers.length ? (
        <div className="py-8 text-sm text-muted-foreground">No saved papers in this track.</div>
      ) : (
        <div className="space-y-3">
          {papers.map((paper, idx) => (
            <PaperCard key={`${paper.paper_id}-${idx}`} paper={paper} rank={idx} />
          ))}
        </div>
      )}
    </div>
  )
}
