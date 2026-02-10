"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import Link from "next/link"
import { Loader2, RefreshCw } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"


type SavedPaperSort = "saved_at" | "judge_score" | "published_at"

type ReadingStatus = "unread" | "reading" | "read" | "archived"

type SavedPaperItem = {
  paper: {
    id: number
    title: string
    authors?: string[]
    source?: string
    venue?: string
    url?: string
    external_url?: string
    published_at?: string | null
  }
  saved_at?: string | null
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
  user_id: string
  items: SavedPaperItem[]
}

type UpdatingAction = "toggleRead" | "unsave"

const PAGE_SIZE_OPTIONS = [10, 20, 50]
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
  const [pageSize, setPageSize] = useState<number>(20)
  const [page, setPage] = useState<number>(1)
  const [loading, setLoading] = useState<boolean>(true)
  const [refreshTick, setRefreshTick] = useState<number>(0)
  const [error, setError] = useState<string | null>(null)
  const [updatingAction, setUpdatingAction] = useState<{ paperId: number; action: UpdatingAction } | null>(null)

  const loadSavedPapers = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const qs = new URLSearchParams({
        sort_by: sortBy,
        limit: "500",
        user_id: "default",
      })
      const res = await fetch(`/api/research/papers/saved?${qs.toString()}`)
      if (!res.ok) {
        throw new Error(await res.text())
      }
      const payload = (await res.json()) as SavedPapersResponse
      setItems(payload.items || [])
      setPage(1)
    } catch (err) {
      const detail = err instanceof Error ? err.message : String(err)
      setError(detail)
      setItems([])
    } finally {
      setLoading(false)
    }
  }, [sortBy])

  useEffect(() => {
    loadSavedPapers().catch(() => {})
  }, [loadSavedPapers, refreshTick])

  const totalPages = useMemo(() => {
    return Math.max(1, Math.ceil(items.length / pageSize))
  }, [items.length, pageSize])

  const pagedItems = useMemo(() => {
    const safePage = Math.min(page, totalPages)
    const start = (safePage - 1) * pageSize
    return items.slice(start, start + pageSize)
  }, [items, page, pageSize, totalPages])

  const updateReadingStatus = useCallback(
    async (
      paperId: number,
      status: ReadingStatus,
      markSaved: boolean | null = null,
      action: UpdatingAction,
    ) => {
      setUpdatingAction({ paperId, action })
      setError(null)
      try {
        const body: Record<string, unknown> = {
          user_id: "default",
          status,
          metadata: {},
        }
        if (markSaved !== null) {
          body.mark_saved = markSaved
        }

        const res = await fetch(`/api/research/papers/${paperId}/status`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        })

        if (!res.ok) {
          throw new Error(await res.text())
        }

        if (markSaved === false) {
          setItems((prev) => prev.filter((row) => row.paper.id !== paperId))
          return
        }

        setItems((prev) =>
          prev.map((row) => {
            if (row.paper.id !== paperId) return row
            return {
              ...row,
              reading_status: {
                ...row.reading_status,
                status,
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
            <label className="text-sm text-muted-foreground" htmlFor="saved-page-size">
              Per page
            </label>
            <select
              id="saved-page-size"
              className="h-9 rounded-md border bg-background px-2 text-sm"
              value={String(pageSize)}
              onChange={(event) => {
                setPageSize(Number(event.target.value || 20))
                setPage(1)
              }}
            >
              {PAGE_SIZE_OPTIONS.map((size) => (
                <option key={size} value={String(size)}>
                  {size}
                </option>
              ))}
            </select>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setRefreshTick((prev) => prev + 1)}
              disabled={loading}
            >
              {loading ? <Loader2 className="mr-1 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-1 h-4 w-4" />}
              Refresh
            </Button>
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
                        <TableCell className="max-w-[520px]">
                          <div className="font-medium">{paper.title}</div>
                          <div className="mt-1 text-xs text-muted-foreground">
                            {(paper.authors || []).slice(0, 4).join(", ") || "Unknown authors"}
                          </div>
                          {paper.venue ? <div className="mt-1 text-xs text-muted-foreground">{paper.venue}</div> : null}
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">{paper.source || "unknown"}</Badge>
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground">
                          <div>{formatDate(item.saved_at)}</div>
                          <div>Published: {formatDate(paper.published_at)}</div>
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
                            onClick={() =>
                              updateReadingStatus(
                                paper.id,
                                status === "read" ? "reading" : "read",
                                true,
                                "toggleRead",
                              )
                            }
                          >
                            {togglingRead ? <Loader2 className="h-3 w-3 animate-spin" /> : status === "read" ? "Reading" : "Mark Read"}
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            disabled={rowUpdating}
                            onClick={() => updateReadingStatus(paper.id, status, false, "unsave")}
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
                Showing {(Math.min(page, totalPages) - 1) * pageSize + 1} -{" "}
                {Math.min(Math.min(page, totalPages) * pageSize, items.length)} of {items.length}
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
    </Card>
  )
}
