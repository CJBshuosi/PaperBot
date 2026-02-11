"use client"

import { useState } from "react"

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

interface CreateTrackModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onCreateTrack: (data: {
    name: string
    description: string
    keywords: string[]
  }) => Promise<void>
  isLoading?: boolean
}

export function CreateTrackModal({
  open,
  onOpenChange,
  onCreateTrack,
  isLoading = false,
}: CreateTrackModalProps) {
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [keywords, setKeywords] = useState("")

  const handleCreate = async () => {
    const trimmedName = name.trim()
    if (!trimmedName) return

    const keywordList = keywords
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean)

    await onCreateTrack({
      name: trimmedName,
      description: description.trim(),
      keywords: keywordList,
    })

    // Reset form
    setName("")
    setDescription("")
    setKeywords("")
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
          <DialogTitle>Create Track</DialogTitle>
          <DialogDescription>
            A track is the isolation boundary for memories, progress, and recommendations.
            Create one for each research topic or project.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="track-name">Name</Label>
            <Input
              id="track-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., RAG Systems, LLM Security"
              disabled={isLoading}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="track-description">Description (optional)</Label>
            <Textarea
              id="track-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe what this track is about..."
              rows={3}
              disabled={isLoading}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="track-keywords">Keywords (optional)</Label>
            <Input
              id="track-keywords"
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
            onClick={handleCreate}
            disabled={isLoading || !name.trim()}
          >
            Create & Activate
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
