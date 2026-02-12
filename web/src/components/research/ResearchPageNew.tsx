"use client"

import { useEffect, useMemo, useState } from "react"
import { useSearchParams } from "next/navigation"

import { cn } from "@/lib/utils"
import { BookOpen } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

import { SearchBox } from "./SearchBox"
import { TrackPills } from "./TrackPills"
import { SearchResults } from "./SearchResults"
import { FeedTab } from "./FeedTab"
import { SavedTab } from "./SavedTab"
import { MemoryTab } from "./MemoryTab"
import { CreateTrackModal } from "./CreateTrackModal"
import { EditTrackModal } from "./EditTrackModal"
import { ManageTracksModal } from "./ManageTracksModal"
import type { Track } from "./TrackSelector"
import type { Paper } from "./PaperCard"
import { BookOpen } from "lucide-react"

type AnchorAuthor = {
  author_id: number
  author_ref?: string
  name: string
  slug: string
  anchor_score: number
  anchor_level: string
  intrinsic_score: number
  relevance_score: number
  evidence_papers: Array<{
    paper_id: number
    title: string
    year?: number | null
    url?: string | null
    citation_count?: number
  }>
}

type ContextPack = {
  context_run_id?: number | null
  routing: {
    track_id: number | null
    stage?: string
    exploration_ratio?: number
    diversity_strength?: number
  }
  paper_recommendations?: Paper[]
  paper_recommendation_reasons?: Record<string, string[]>
}

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init)
  if (!res.ok) {
    const text = await res.text().catch(() => "")
    throw new Error(`${res.status} ${res.statusText} ${text}`.trim())
  }
  return res.json() as Promise<T>
}

function getGreeting(): string {
  const hour = new Date().getHours()
  if (hour < 12) return "Good morning"
  if (hour < 18) return "Good afternoon"
  return "Good evening"
}

export default function ResearchPageNew() {
  const searchParams = useSearchParams()

  // User state
  const [userId] = useState("default")

  // Track state
  const [tracks, setTracks] = useState<Track[]>([])
  const [activeTrackId, setActiveTrackId] = useState<number | null>(null)

  // Search state
  const [query, setQuery] = useState("")
  const [hasSearched, setHasSearched] = useState(false)
  const [isSearching, setIsSearching] = useState(false)
  const [contextPack, setContextPack] = useState<ContextPack | null>(null)
  const [activeTab, setActiveTab] = useState("search")
  const [searchSources, setSearchSources] = useState<string[]>(["semantic_scholar"])

  // Anchor state
  const [anchors, setAnchors] = useState<AnchorAuthor[]>([])
  const [anchorsLoading, setAnchorsLoading] = useState(false)
  const [anchorsError, setAnchorsError] = useState<string | null>(null)

  // UI state
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)
  const [editModalOpen, setEditModalOpen] = useState(false)
  const [editError, setEditError] = useState<string | null>(null)
  const [trackToEdit, setTrackToEdit] = useState<Track | null>(null)
  const [manageModalOpen, setManageModalOpen] = useState(false)
  const [confirmClearOpen, setConfirmClearOpen] = useState(false)
  const [trackToClear, setTrackToClear] = useState<number | null>(null)

  // Derived state
  const activeTrack = useMemo(
    () => tracks.find((t) => t.id === activeTrackId) || null,
    [tracks, activeTrackId]
  )

  const papers = contextPack?.paper_recommendations || []
  const reasons = contextPack?.paper_recommendation_reasons || {}
  const routeTrackId = Number(searchParams.get("track_id") || 0)

  // Load tracks on mount
  useEffect(() => {
    refreshTracks().catch((e) => setError(String(e)))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!routeTrackId || !Number.isFinite(routeTrackId)) return
    if (!tracks.some((track) => track.id === routeTrackId)) return
    if (activeTrackId === routeTrackId) return
    activateTrack(routeTrackId).catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [routeTrackId, tracks, activeTrackId])

  useEffect(() => {
    if (!activeTrackId) {
      setAnchors([])
      setAnchorsError(null)
      setAnchorsLoading(false)
      return
    }

    let cancelled = false
    setAnchorsLoading(true)
    setAnchorsError(null)

    fetchJson<{ items: AnchorAuthor[] }>(
      `/api/research/tracks/${activeTrackId}/anchors/discover?user_id=${encodeURIComponent(userId)}&limit=5&window_days=730`
    )
      .then((data) => {
        if (cancelled) return
        setAnchors(data.items || [])
      })
      .catch((e) => {
        if (cancelled) return
        setAnchors([])
        setAnchorsError(String(e))
      })
      .finally(() => {
        if (!cancelled) {
          setAnchorsLoading(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [activeTrackId, userId])

  async function refreshTracks(): Promise<number | null> {
    const data = await fetchJson<{ tracks: Track[] }>(
      `/api/research/tracks?user_id=${encodeURIComponent(userId)}`
    )
    setTracks(data.tracks || [])
    const active = data.tracks.find((t) => t.is_active)
    const activeId = active?.id ?? null
    setActiveTrackId(activeId)
    return activeId
  }

  async function activateTrack(trackId: number) {
    setLoading(true)
    try {
      await fetchJson(
        `/api/research/tracks/${trackId}/activate?user_id=${encodeURIComponent(userId)}`,
        {
          method: "POST",
          body: "{}",
          headers: { "Content-Type": "application/json" },
        }
      )
      await refreshTracks()
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }

  async function handleSearch() {
    if (!query.trim()) return

    setIsSearching(true)
    setHasSearched(true)
    setError(null)

    try {
      const body = {
        user_id: userId,
        query,
        paper_limit: 10,
        memory_limit: 8,
        sources: searchSources,
        offline: false,
        include_cross_track: false,
        stage: "auto",
      }

      const data = await fetchJson<{ context_pack: ContextPack }>(
        `/api/research/context`,
        {
          method: "POST",
          body: JSON.stringify(body),
          headers: { "Content-Type": "application/json" },
        }
      )

      setContextPack(data.context_pack)
      setActiveTab("search")
    } catch (e) {
      setError(String(e))
    } finally {
      setIsSearching(false)
    }
  }

  function toggleSearchSource(source: string) {
    setSearchSources((prev) => {
      const exists = prev.includes(source)
      if (exists) {
        const next = prev.filter((x) => x !== source)
        return next.length ? next : ["semantic_scholar"]
      }
      return [...prev, source]
    })
  }

  async function handleCreateTrack(data: {
    name: string
    description: string
    keywords: string[]
  }): Promise<boolean> {
    const name = data.name.trim()
    const duplicate = tracks.some((track) => track.name.trim() === name)
    if (duplicate) {
      setCreateError(`Track "${name}" already exists.`)
      return false
    }
    setLoading(true)
    setError(null)
    setCreateError(null)
    try {
      await fetchJson(`/api/research/tracks`, {
        method: "POST",
        body: JSON.stringify({
          user_id: userId,
          name,
          description: data.description,
          keywords: data.keywords,
          activate: true,
        }),
        headers: { "Content-Type": "application/json" },
      })
      setCreateModalOpen(false)
      setCreateError(null)
      await refreshTracks()
      return true
    } catch (e) {
      const message = String(e)
      if (message.startsWith("409")) {
        setCreateError(`Track "${name}" already exists.`)
      } else {
        setCreateError(message)
      }
      return false
    } finally {
      setLoading(false)
    }
  }

  function handleEditTrack(track: Track) {
    setTrackToEdit(track)
    setEditError(null)
    setEditModalOpen(true)
  }

  async function handleUpdateTrack(
    trackId: number,
    data: { name: string; description: string; keywords: string[] }
  ): Promise<boolean> {
    const name = data.name.trim()
    const duplicate = tracks.some(
      (track) => track.id !== trackId && track.name.trim() === name
    )
    if (duplicate) {
      setEditError(`Track "${name}" already exists.`)
      return false
    }
    setLoading(true)
    setError(null)
    setEditError(null)
    try {
      await fetchJson(`/api/research/tracks/${trackId}?user_id=${encodeURIComponent(userId)}`, {
        method: "PATCH",
        body: JSON.stringify({
          name,
          description: data.description,
          keywords: data.keywords,
        }),
        headers: { "Content-Type": "application/json" },
      })
      await refreshTracks()
      return true
    } catch (e) {
      const message = String(e)
      if (message.startsWith("409")) {
        setEditError(`Track "${name}" already exists.`)
      } else {
        setEditError(message)
      }
      return false
    } finally {
      setLoading(false)
    }
  }

  async function handleClearTrackMemory(trackId: number) {
    setTrackToClear(trackId)
    setConfirmClearOpen(true)
  }

  async function confirmClearMemory() {
    if (!trackToClear) return

    setLoading(true)
    setError(null)
    try {
      await fetchJson(
        `/api/research/tracks/${trackToClear}/memory/clear?user_id=${encodeURIComponent(userId)}&confirm=true`,
        {
          method: "POST",
          body: "{}",
          headers: { "Content-Type": "application/json" },
        }
      )
      setConfirmClearOpen(false)
      setTrackToClear(null)
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }

  async function handleFeedback(
    paperId: string,
    action: string,
    rank?: number,
    paper?: Paper
  ): Promise<void> {
    // Don't set global loading - PaperCard handles its own loading state
    setError(null)
    const body: Record<string, unknown> = {
      user_id: userId,
      track_id: activeTrackId,
      paper_id: paperId,
      action,
      weight: 0.0,
      context_run_id: contextPack?.context_run_id ?? null,
      context_rank: typeof rank === "number" ? rank : undefined,
      metadata: {},
    }

    // Include paper metadata for save action
    if (action === "save" && paper) {
      body.paper_title = paper.title
      body.paper_abstract = paper.abstract || ""
      body.paper_authors = paper.authors || []
      body.paper_year = paper.year
      body.paper_venue = paper.venue
      body.paper_citation_count = paper.citation_count
      body.paper_url = paper.url
    }

    await fetchJson(`/api/research/papers/feedback`, {
      method: "POST",
      body: JSON.stringify(body),
      headers: { "Content-Type": "application/json" },
    })
  }

  const trackToClearName = tracks.find((t) => t.id === trackToClear)?.name || "this track"

  return (
    <div className={cn("min-h-[calc(100vh-4rem)] pt-6 sm:pt-8 transition-all duration-500 ease-out")}>
      {/* Confirm Clear Memory Dialog */}
      <Dialog open={confirmClearOpen} onOpenChange={setConfirmClearOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Clear Track Memory?</DialogTitle>
            <DialogDescription>
              This will delete all memories for &quot;{trackToClearName}&quot;. This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setConfirmClearOpen(false)
                setTrackToClear(null)
              }}
              disabled={loading}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={confirmClearMemory}
              disabled={loading}
            >
              Clear Memory
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Create Track Modal */}
      <CreateTrackModal
        open={createModalOpen}
        onOpenChange={(open) => {
          setCreateModalOpen(open)
          if (!open) setCreateError(null)
        }}
        onCreateTrack={handleCreateTrack}
        isLoading={loading}
        error={createError}
        onClearError={() => setCreateError(null)}
      />

      {/* Edit Track Modal */}
      <EditTrackModal
        open={editModalOpen}
        onOpenChange={(open) => {
          setEditModalOpen(open)
          if (!open) {
            setTrackToEdit(null)
            setEditError(null)
          }
        }}
        track={trackToEdit}
        onUpdateTrack={handleUpdateTrack}
        isLoading={loading}
        error={editError}
        onClearError={() => setEditError(null)}
      />

      {/* Manage Tracks Modal */}
      <ManageTracksModal
        open={manageModalOpen}
        onOpenChange={setManageModalOpen}
        tracks={tracks}
        activeTrackId={activeTrackId}
        onEditTrack={handleEditTrack}
        onClearTrackMemory={handleClearTrackMemory}
        isLoading={loading}
      />

      {/* Main Content */}
      <div
        className={cn(
          "w-full px-4 sm:px-6 transition-all duration-500 ease-out",
          "max-w-5xl mx-auto"
        )}
      >
        {/* Greeting - only show before search */}
        {!hasSearched && (
          <div className="text-center mb-8 sm:mb-10 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <h1 className="text-3xl sm:text-4xl md:text-5xl font-semibold tracking-tight mb-2 sm:mb-3">
              <BookOpen className="inline-block mr-2 sm:mr-3 h-8 w-8 sm:h-10 sm:w-10 align-middle" />
              {getGreeting()}
            </h1>
            <p className="text-lg sm:text-xl text-muted-foreground">
              What papers are you looking for?
            </p>
          </div>
        )}

        {/* Search Box */}
        <div
          className={cn(
            "transition-all duration-500 ease-out",
            hasSearched ? "mb-6" : "mb-10"
          )}
        >
          <SearchBox
            query={query}
            onQueryChange={setQuery}
            onSearch={handleSearch}
            tracks={tracks}
            activeTrack={activeTrack}
            onSelectTrack={activateTrack}
            onNewTrack={() => setCreateModalOpen(true)}
            onManageTracks={() => setManageModalOpen(true)}
            isSearching={isSearching}
            disabled={loading}
          />
        </div>

        {/* Track Pills - only show before search */}
        {!hasSearched && tracks.length > 0 && (
          <div className="mb-8 animate-in fade-in slide-in-from-bottom-2 duration-500 delay-150">
            <TrackPills
              tracks={tracks}
              activeTrackId={activeTrackId}
              onSelectTrack={activateTrack}
              onNewTrack={() => setCreateModalOpen(true)}
              disabled={loading}
            />
          </div>
        )}

        {activeTrack && (
          <Card className="mb-6 border-border/60">
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Anchor Authors · {activeTrack.name}</CardTitle>
            </CardHeader>
            <CardContent>
              {anchorsLoading ? (
                <p className="text-sm text-muted-foreground">Loading anchor authors...</p>
              ) : anchorsError ? (
                <p className="text-sm text-destructive">Failed to load anchors: {anchorsError}</p>
              ) : anchors.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No anchor authors yet for this track. Try searching and saving a few papers first.
                </p>
              ) : (
                <div className="space-y-3">
                  {anchors.map((anchor) => {
                    const evidence = anchor.evidence_papers?.[0]
                    return (
                      <div
                        key={`${anchor.author_id}-${anchor.slug}`}
                        className="rounded-md border border-border/60 p-3"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div className="font-medium">{anchor.name}</div>
                          <div className="flex items-center gap-2 text-xs">
                            <span className="rounded-full bg-muted px-2 py-1 uppercase tracking-wide">
                              {anchor.anchor_level}
                            </span>
                            <span className="text-muted-foreground">
                              score {anchor.anchor_score.toFixed(2)}
                            </span>
                          </div>
                        </div>
                        {evidence ? (
                          <div className="mt-1 text-xs text-muted-foreground">
                            Evidence: {evidence.url ? (
                              <a
                                href={evidence.url}
                                target="_blank"
                                rel="noreferrer"
                                className="underline underline-offset-2"
                              >
                                {evidence.title}
                              </a>
                            ) : (
                              <span>{evidence.title}</span>
                            )}
                          </div>
                        ) : (
                          <div className="mt-1 text-xs text-amber-600 dark:text-amber-400">
                            No evidence papers available yet.
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Error Display */}
        {error && (
          <Card className="border-destructive/40 mb-6 max-w-3xl mx-auto">
            <CardHeader className="pb-2">
              <CardTitle className="text-destructive text-base">Error</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="whitespace-pre-wrap text-sm">{error}</pre>
            </CardContent>
          </Card>
        )}

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="mb-4 grid w-full grid-cols-4">
            <TabsTrigger value="search">Search</TabsTrigger>
            <TabsTrigger value="feed">Feed</TabsTrigger>
            <TabsTrigger value="saved">Saved</TabsTrigger>
            <TabsTrigger value="memory">Memory</TabsTrigger>
          </TabsList>

          <TabsContent value="search">
            <SearchResults
              papers={papers}
              reasons={reasons}
              isSearching={isSearching}
              hasSearched={hasSearched}
              selectedSources={searchSources}
              onToggleSource={toggleSearchSource}
              onLike={(paperId, rank) => handleFeedback(paperId, "like", rank)}
              onSave={(paperId, rank, paper) => handleFeedback(paperId, "save", rank, paper)}
              onDislike={(paperId, rank) => handleFeedback(paperId, "dislike", rank)}
            />
          </TabsContent>

          <TabsContent value="feed">
            <FeedTab
              userId={userId}
              trackId={activeTrackId}
              onLike={(paperId, rank) => handleFeedback(paperId, "like", rank)}
              onSave={(paperId, rank, paper) => handleFeedback(paperId, "save", rank, paper)}
              onDislike={(paperId, rank) => handleFeedback(paperId, "dislike", rank)}
            />
          </TabsContent>

          <TabsContent value="saved">
            <SavedTab userId={userId} trackId={activeTrackId} />
          </TabsContent>

          <TabsContent value="memory">
            <MemoryTab userId={userId} trackId={activeTrackId} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}
