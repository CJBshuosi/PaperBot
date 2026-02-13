"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import Link from "next/link"
import { Check, ChevronDown, Copy, Download, FileText, Filter, Loader2 } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Input } from "@/components/ui/input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"


type SavedPaperSort = "saved_at" | "judge_score" | "published_at"

type ReadingStatus = "unread" | "reading" | "read" | "archived"

type SavedPaperItem = {
  paper: {
    id: number
    title: string
    authors?: string[]
    primary_source?: string
    source?: string
    venue?: string
    url?: string
    external_url?: string
    published_at?: string | null
    publication_date?: string | null
    citation_count?: number
  }
  saved_at?: string | null
  track_id?: number | null
  action?: string
  reading_status?: {
    status?: string
    updated_at?: string | null
  } | null
  latest_judge?: {
    overall?: number | null
    recommendation?: string | null
  } | null
}

type SavedPapersResponse = {
  papers: SavedPaperItem[]
  total: number
  limit: number
  offset: number
}

type UpdatingAction = "toggleRead" | "unsave"

type Track = {
  id: number
  name: string
  is_active?: boolean
}

const PAGE_SIZE = 20
const SORT_OPTIONS: Array<{ value: SavedPaperSort; label: string }> = [
  { value: "saved_at", label: "Saved Time" },
  { value: "judge_score", label: "Judge Score" },
  { value: "published_at", label: "Published Time" },
]

function formatDate(value?: string | null): string {
  if (!value) return "-"
  const dt = new Date(value)
  if (Number.isNaN(dt.getTime())) return "-"
  return dt.toLocaleString()
}

function formatJudge(value?: number | null): string {
  if (typeof value !== "number") return "-"
  return `${value.toFixed(2)} / 5.0`
}

function normalizeStatus(value?: string | null): ReadingStatus {
  if (value === "reading" || value === "read" || value === "archived") return value
  return "unread"
}

export default function SavedPapersList() {
  const [items, setItems] = useState<SavedPaperItem[]>([])
  const [sortBy, setSortBy] = useState<SavedPaperSort>("saved_at")
  const [page, setPage] = useState<number>(1)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [updatingAction, setUpdatingAction] = useState<{ paperId: number; action: UpdatingAction } | null>(null)

  // Related Work state
  const [rwOpen, setRwOpen] = useState(false)
  const [rwTopic, setRwTopic] = useState("")
  const [rwLoading, setRwLoading] = useState(false)
  const [rwMarkdown, setRwMarkdown] = useState<string | null>(null)
  const [rwCopied, setRwCopied] = useState(false)

  // Selection state
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())

  // Track filter state
  const [tracks, setTracks] = useState<Track[]>([])
  const [selectedTrackId, setSelectedTrackId] = useState<number | null>(null)

  // Fetch tracks on mount
  useEffect(() => {
    fetch("/api/research/tracks?user_id=default", { cache: "no-store" })
      .then((res) => res.json())
      .then((data) => setTracks(data.tracks || []))
      .catch(() => setTracks([]))
  }, [])

  const loadSavedPapers = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const qs = new URLSearchParams({
        sort_by: sortBy,
        sort_order: "desc",
        limit: "500",
        user_id: "default",
      })
      if (selectedTrackId) {
        qs.set("track_id", String(selectedTrackId))
      }
      const res = await fetch(`/api/papers/library?${qs.toString()}`, { cache: "no-store" })
      if (!res.ok) {
        const errorText = await res.text()
        // Avoid showing raw HTML in error messages
        if (errorText.startsWith("<!DOCTYPE") || errorText.startsWith("<html")) {
          throw new Error(`Server error: ${res.status} ${res.statusText}`)
        }
        throw new Error(errorText)
      }
      const payload = (await res.json()) as SavedPapersResponse
      setItems(payload.papers || [])
      setPage(1)
      setSelectedIds(new Set()) // Clear selection on reload
    } catch (err) {
      const detail = err instanceof Error ? err.message : String(err)
      setError(detail)
      setItems([])
    } finally {
      setLoading(false)
    }
  }, [sortBy, selectedTrackId])

  useEffect(() => {
    loadSavedPapers().catch(() => {})
  }, [loadSavedPapers])

  const totalPages = useMemo(() => {
    return Math.max(1, Math.ceil(items.length / PAGE_SIZE))
  }, [items.length])

  const pagedItems = useMemo(() => {
    const safePage = Math.min(page, totalPages)
    const start = (safePage - 1) * PAGE_SIZE
    return items.slice(start, start + PAGE_SIZE)
  }, [items, page, totalPages])

  const hasSelection = selectedIds.size > 0

  const toggleSelect = useCallback((paperId: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(paperId)) {
        next.delete(paperId)
      } else {
        next.add(paperId)
      }
      return next
    })
  }, [])

  const toggleSelectAll = useCallback(() => {
    if (selectedIds.size === pagedItems.length && pagedItems.length > 0) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(pagedItems.map((item) => item.paper.id)))
    }
  }, [selectedIds.size, pagedItems])

  const isAllSelected = pagedItems.length > 0 && selectedIds.size === pagedItems.length

  const unsavePaper = useCallback(async (paperId: number) => {
    setUpdatingAction({ paperId, action: "unsave" })
    setError(null)
    try {
      const res = await fetch(`/api/papers/${paperId}/save?user_id=default`, {
        method: "DELETE",
      })

      if (!res.ok) {
        const errorText = await res.text()
        if (errorText.startsWith("<!DOCTYPE") || errorText.startsWith("<html")) {
          throw new Error(`Server error: ${res.status} ${res.statusText}`)
        }
        throw new Error(errorText)
      }

      setItems((prev) => prev.filter((row) => row.paper.id !== paperId))
    } catch (err) {
      const detail = err instanceof Error ? err.message : String(err)
      setError(detail)
    } finally {
      setUpdatingAction(null)
    }
  }, [])

  const toggleReadStatus = useCallback(
    async (paperId: number, currentStatus: ReadingStatus) => {
      setUpdatingAction({ paperId, action: "toggleRead" })
      setError(null)
      const newStatus = currentStatus === "read" ? "reading" : "read"
      try {
        // Use the paper feedback endpoint with action to track reading status
        const res = await fetch(`/api/research/papers/feedback`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_id: "default",
            paper_id: String(paperId),
            action: newStatus,
            weight: 1.0,
            metadata: { reading_status: newStatus },
          }),
        })

        if (!res.ok) {
          const errorText = await res.text()
          if (errorText.startsWith("<!DOCTYPE") || errorText.startsWith("<html")) {
            throw new Error(`Server error: ${res.status} ${res.statusText}`)
          }
          throw new Error(errorText)
        }

        setItems((prev) =>
          prev.map((row) => {
            if (row.paper.id !== paperId) return row
            return {
              ...row,
              reading_status: {
                ...row.reading_status,
                status: newStatus,
                updated_at: new Date().toISOString(),
              },
            }
          }),
        )
      } catch (err) {
        const detail = err instanceof Error ? err.message : String(err)
        setError(detail)
      } finally {
        setUpdatingAction(null)
      }
    },
    [],
  )

  const handleExport = useCallback(async (format: "bibtex" | "ris" | "markdown" | "csl_json") => {
    const qs = new URLSearchParams({ format, user_id: "default" })
    // Add selected paper IDs
    selectedIds.forEach((id) => qs.append("paper_id", String(id)))
    try {
      const res = await fetch(`/api/papers/export?${qs.toString()}`, { cache: "no-store" })
      if (!res.ok) throw new Error(`${res.status}`)
      const blob = await res.blob()
      const extMap: Record<string, string> = { bibtex: "bib", ris: "ris", markdown: "md", csl_json: "csl.json" }
      const ext = extMap[format] || "txt"
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `papers.${ext}`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      setError("Export failed")
    }
  }, [selectedIds])

  const handleGenerateRelatedWork = useCallback(async () => {
    if (!rwTopic.trim()) return
    setRwLoading(true)
    setRwMarkdown(null)
    try {
      const res = await fetch("/api/research/papers/related-work", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: "default",
          topic: rwTopic.trim(),
        }),
      })
      if (!res.ok) throw new Error(`${res.status}`)
      const data = await res.json()
      setRwMarkdown(data.markdown || "No output generated.")
    } catch {
      setRwMarkdown("Failed to generate related work. Please try again.")
    } finally {
      setRwLoading(false)
    }
  }, [rwTopic])

  const handleCopyRw = useCallback(async () => {
    if (!rwMarkdown) return
    await navigator.clipboard.writeText(rwMarkdown)
    setRwCopied(true)
    setTimeout(() => setRwCopied(false), 2000)
  }, [rwMarkdown])

  return (
    <Card>
      <CardHeader className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <CardTitle>Saved Papers</CardTitle>
            <CardDescription>
              View saved items, sort by score/time, and update reading status.
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-sm text-muted-foreground" htmlFor="saved-sort">
              Sort
            </label>
            <select
              id="saved-sort"
              className="h-9 rounded-md border bg-background px-2 text-sm"
              value={sortBy}
              onChange={(event) => setSortBy(event.target.value as SavedPaperSort)}
            >
              {SORT_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" disabled={loading}>
                  <Filter className="mr-1 h-4 w-4" />
                  {selectedTrackId
                    ? tracks.find((t) => t.id === selectedTrackId)?.name || "Track"
                    : "All Tracks"}
                  <ChevronDown className="ml-1 h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48">
                <DropdownMenuItem
                  onClick={() => setSelectedTrackId(null)}
                  className="flex items-center gap-2"
                >
                  {selectedTrackId === null ? <Check className="h-4 w-4" /> : <span className="w-4" />}
                  All Tracks
                </DropdownMenuItem>
                {tracks.length > 0 && <DropdownMenuSeparator />}
                {tracks.map((track) => (
                  <DropdownMenuItem
                    key={track.id}
                    onClick={() => setSelectedTrackId(track.id)}
                    className="flex items-center gap-2"
                  >
                    {selectedTrackId === track.id ? <Check className="h-4 w-4" /> : <span className="w-4" />}
                    <span className="truncate">{track.name}</span>
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
            <Button
              variant="outline"
              size="sm"
              disabled={loading || items.length === 0}
              onClick={() => { setRwOpen(true); setRwMarkdown(null); setRwTopic(""); }}
            >
              <FileText className="mr-1 h-4 w-4" />
              Related Work
            </Button>
            {hasSelection && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="sm" disabled={loading}>
                    <Download className="mr-1 h-4 w-4" />
                    Export ({selectedIds.size})
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={() => handleExport("bibtex")}>BibTeX</DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handleExport("ris")}>RIS</DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handleExport("markdown")}>Markdown</DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handleExport("csl_json")}>Zotero (CSL-JSON)</DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            )}
          </div>
        </div>
        {error ? <p className="text-sm text-destructive">{error}</p> : null}
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex items-center gap-2 py-8 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading saved papers...
          </div>
        ) : items.length === 0 ? (
          <div className="py-8 text-sm text-muted-foreground">No saved papers yet.</div>
        ) : (
          <>
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[50px]">
                      <Checkbox
                        checked={isAllSelected}
                        onCheckedChange={toggleSelectAll}
                        aria-label="Select all"
                      />
                    </TableHead>
                    <TableHead>Title</TableHead>
                    <TableHead>Source</TableHead>
                    <TableHead>Saved</TableHead>
                    <TableHead>Judge</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {pagedItems.map((item) => {
                    const paper = item.paper
                    const status = normalizeStatus(item.reading_status?.status)
                    const togglingRead =
                      updatingAction?.paperId === paper.id && updatingAction?.action === "toggleRead"
                    const unsaving =
                      updatingAction?.paperId === paper.id && updatingAction?.action === "unsave"
                    const rowUpdating = togglingRead || unsaving
                    return (
                      <TableRow key={paper.id}>
                        <TableCell>
                          <Checkbox
                            checked={selectedIds.has(paper.id)}
                            onCheckedChange={() => toggleSelect(paper.id)}
                            aria-label={`Select ${paper.title}`}
                          />
                        </TableCell>
                        <TableCell className="max-w-[480px]">
                          <div className="font-medium">{paper.title}</div>
                          <div className="mt-1 text-xs text-muted-foreground">
                            {(paper.authors || []).slice(0, 4).join(", ") || "Unknown authors"}
                          </div>
                          {paper.venue ? <div className="mt-1 text-xs text-muted-foreground">{paper.venue}</div> : null}
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">{paper.primary_source || paper.source || "unknown"}</Badge>
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground">
                          <div>{formatDate(item.saved_at)}</div>
                          <div>Published: {formatDate(paper.publication_date || paper.published_at)}</div>
                        </TableCell>
                        <TableCell>
                          <div className="text-sm">{formatJudge(item.latest_judge?.overall)}</div>
                          {item.latest_judge?.recommendation ? (
                            <div className="text-xs text-muted-foreground">{item.latest_judge.recommendation}</div>
                          ) : null}
                        </TableCell>
                        <TableCell>
                          <Badge>{status}</Badge>
                        </TableCell>
                        <TableCell className="space-x-2 text-right">
                          <Button asChild size="sm" variant="outline">
                            <Link href={`/papers/${paper.id}`}>Detail</Link>
                          </Button>
                          <Button
                            size="sm"
                            variant="secondary"
                            disabled={rowUpdating}
                            onClick={() => toggleReadStatus(paper.id, status)}
                          >
                            {togglingRead ? <Loader2 className="h-3 w-3 animate-spin" /> : status === "read" ? "Reading" : "Mark Read"}
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            disabled={rowUpdating}
                            onClick={() => unsavePaper(paper.id)}
                          >
                            {unsaving ? <Loader2 className="h-3 w-3 animate-spin" /> : "Unsave"}
                          </Button>
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            </div>
            <div className="mt-3 flex items-center justify-between text-sm text-muted-foreground">
              <span>
                Showing {(Math.min(page, totalPages) - 1) * PAGE_SIZE + 1} -{" "}
                {Math.min(Math.min(page, totalPages) * PAGE_SIZE, items.length)} of {items.length}
              </span>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page <= 1}
                  onClick={() => setPage((prev) => Math.max(1, prev - 1))}
                >
                  Prev
                </Button>
                <span>
                  Page {Math.min(page, totalPages)} / {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page >= totalPages}
                  onClick={() => setPage((prev) => Math.min(totalPages, prev + 1))}
                >
                  Next
                </Button>
              </div>
            </div>
          </>
        )}
      </CardContent>

      {/* Related Work Dialog */}
      <Dialog open={rwOpen} onOpenChange={setRwOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Generate Related Work</DialogTitle>
            <DialogDescription>
              Generate a Related Work section draft from your saved papers.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="flex gap-2">
              <Input
                placeholder="Enter research topic..."
                value={rwTopic}
                onChange={(e) => setRwTopic(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") handleGenerateRelatedWork() }}
                disabled={rwLoading}
              />
              <Button onClick={handleGenerateRelatedWork} disabled={rwLoading || !rwTopic.trim()}>
                {rwLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Generate"}
              </Button>
            </div>
            {rwMarkdown && (
              <div className="rounded-md border bg-muted/50 p-4">
                <pre className="whitespace-pre-wrap text-sm font-mono">{rwMarkdown}</pre>
              </div>
            )}
          </div>
          {rwMarkdown && (
            <DialogFooter>
              <Button variant="outline" size="sm" onClick={handleCopyRw}>
                <Copy className="mr-1 h-3.5 w-3.5" />
                {rwCopied ? "Copied" : "Copy"}
              </Button>
            </DialogFooter>
          )}
        </DialogContent>
      </Dialog>
    </Card>
  )
}
