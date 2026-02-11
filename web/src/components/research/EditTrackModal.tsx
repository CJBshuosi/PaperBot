"use client"

import { useEffect, useState } from "react"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"

import type { Track } from "./TrackSelector"

interface EditTrackModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  track: Track | null
  onUpdateTrack: (
    trackId: number,
    data: {
      name: string
      description: string
      keywords: string[]
    }
  ) => Promise<void>
  isLoading?: boolean
}

export function EditTrackModal({
  open,
  onOpenChange,
  track,
  onUpdateTrack,
  isLoading = false,
}: EditTrackModalProps) {
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [keywords, setKeywords] = useState("")

  // Populate form when track changes
  useEffect(() => {
    if (track) {
      setName(track.name)
      setDescription(track.description || "")
      setKeywords(track.keywords?.join(", ") || "")
    }
  }, [track])

  const handleUpdate = async () => {
    if (!track) return
    const trimmedName = name.trim()
    if (!trimmedName) return

    const keywordList = keywords
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean)

    await onUpdateTrack(track.id, {
      name: trimmedName,
      description: description.trim(),
      keywords: keywordList,
    })

    onOpenChange(false)
  }

  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      // Reset form when closing
      setName("")
      setDescription("")
      setKeywords("")
    }
    onOpenChange(newOpen)
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit Track</DialogTitle>
          <DialogDescription>
            Update the track name, description, and keywords.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="edit-track-name">Name</Label>
            <Input
              id="edit-track-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., RAG Systems, LLM Security"
              disabled={isLoading}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="edit-track-description">Description (optional)</Label>
            <Textarea
              id="edit-track-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe what this track is about..."
              rows={3}
              disabled={isLoading}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="edit-track-keywords">Keywords (optional)</Label>
            <Input
              id="edit-track-keywords"
              value={keywords}
              onChange={(e) => setKeywords(e.target.value)}
              placeholder="retrieval, augmented generation, reranking"
              disabled={isLoading}
            />
            <p className="text-xs text-muted-foreground">
              Comma-separated keywords to help with paper recommendations
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => handleOpenChange(false)}
            disabled={isLoading}
          >
            Cancel
          </Button>
          <Button
            onClick={handleUpdate}
            disabled={isLoading || !name.trim()}
          >
            Save Changes
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
