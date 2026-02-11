"use client"

import { Pencil, Trash2 } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { ScrollArea } from "@/components/ui/scroll-area"

import type { Track } from "./TrackSelector"

interface ManageTracksModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  tracks: Track[]
  activeTrackId: number | null
  onEditTrack: (track: Track) => void
  onClearTrackMemory: (trackId: number) => void
  isLoading?: boolean
}

export function ManageTracksModal({
  open,
  onOpenChange,
  tracks,
  activeTrackId,
  onEditTrack,
  onClearTrackMemory,
  isLoading = false,
}: ManageTracksModalProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Manage Tracks</DialogTitle>
          <DialogDescription>
            View and manage your research tracks. Clear memory to reset a track&apos;s context.
          </DialogDescription>
        </DialogHeader>

        <ScrollArea className="max-h-[400px] pr-4">
          <div className="space-y-3 py-4">
            {tracks.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">
                No tracks yet. Create one to get started.
              </p>
            ) : (
              tracks.map((track) => (
                <div
                  key={track.id}
                  className="flex items-start justify-between gap-3 rounded-lg border p-3"
                >
                  <div className="space-y-1 flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium truncate">{track.name}</span>
                      {track.id === activeTrackId && (
                        <Badge variant="secondary" className="text-xs">
                          Active
                        </Badge>
                      )}
                    </div>
                    {track.description && (
                      <p className="text-xs text-muted-foreground line-clamp-2">
                        {track.description}
                      </p>
                    )}
                    {track.keywords && track.keywords.length > 0 && (
                      <div className="flex flex-wrap gap-1 pt-1">
                        {track.keywords.slice(0, 4).map((keyword) => (
                          <Badge
                            key={keyword}
                            variant="outline"
                            className="text-[10px]"
                          >
                            {keyword}
                          </Badge>
                        ))}
                        {track.keywords.length > 4 && (
                          <span className="text-[10px] text-muted-foreground">
                            +{track.keywords.length - 4} more
                          </span>
                        )}
                      </div>
                    )}
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => onEditTrack(track)}
                      disabled={isLoading}
                    >
                      <Pencil className="h-3.5 w-3.5 mr-1.5" />
                      Edit
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="text-destructive hover:text-destructive hover:bg-destructive/10"
                      onClick={() => onClearTrackMemory(track.id)}
                      disabled={isLoading}
                      title="Clear track memory"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))
            )}
          </div>
        </ScrollArea>

      </DialogContent>
    </Dialog>
  )
}
