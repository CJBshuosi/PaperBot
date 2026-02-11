"use client"

import { useEffect, useMemo, useState } from "react"

import { cn } from "@/lib/utils"
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

import { SearchBox } from "./SearchBox"
import { TrackPills } from "./TrackPills"
import { SearchResults } from "./SearchResults"
import { CreateTrackModal } from "./CreateTrackModal"
import { EditTrackModal } from "./EditTrackModal"
import { ManageTracksModal } from "./ManageTracksModal"
import type { Track } from "./TrackSelector"
import type { Paper } from "./PaperCard"

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

  // Load tracks on mount
  useEffect(() => {
    refreshTracks().catch((e) => setError(String(e)))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

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
    } catch (e) {
      setError(String(e))
    } finally {
      setIsSearching(false)
    }
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
    <div
      className={cn(
        "min-h-[calc(100vh-4rem)] transition-all duration-500 ease-out",
        hasSearched
          ? "pt-8"
          : "flex flex-col items-center justify-center"
      )}
    >
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
          hasSearched ? "max-w-5xl mx-auto" : "max-w-3xl"
        )}
      >
        {/* Greeting - only show before search */}
        {!hasSearched && (
          <div className="text-center mb-8 sm:mb-10 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <h1 className="text-3xl sm:text-4xl md:text-5xl font-semibold tracking-tight mb-2 sm:mb-3">
              <span className="mr-2 sm:mr-3">📚</span>
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
          <div className="animate-in fade-in slide-in-from-bottom-2 duration-500 delay-150">
            <TrackPills
              tracks={tracks}
              activeTrackId={activeTrackId}
              onSelectTrack={activateTrack}
              onNewTrack={() => setCreateModalOpen(true)}
              disabled={loading}
            />
          </div>
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

        {/* Search Results */}
        <SearchResults
          papers={papers}
          reasons={reasons}
          isSearching={isSearching}
          hasSearched={hasSearched}
          onLike={(paperId, rank) => handleFeedback(paperId, "like", rank)}
          onSave={(paperId, rank, paper) => handleFeedback(paperId, "save", rank, paper)}
          onDislike={(paperId, rank) => handleFeedback(paperId, "dislike", rank)}
        />
      </div>
    </div>
  )
}
