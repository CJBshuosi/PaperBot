"use client"

import { useState } from "react"
import { Check, ExternalLink, Heart, Loader2, Save, ThumbsDown } from "lucide-react"

import { cn, safeHref } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"

export type Paper = {
  paper_id: string
  title: string
  abstract?: string
  year?: number
  venue?: string
  citation_count?: number
  authors?: string[]
  url?: string
}

interface PaperCardProps {
  paper: Paper
  rank?: number
  reasons?: string[]
  onLike?: () => Promise<void> | void
  onSave?: () => Promise<void> | void
  onDislike?: () => Promise<void> | void
  isLoading?: boolean
  className?: string
}

export function PaperCard({
  paper,
  rank,
  reasons,
  onLike,
  onSave,
  onDislike,
  isLoading = false,
  className,
}: PaperCardProps) {
  const [isSaved, setIsSaved] = useState(false)
  const [isLiked, setIsLiked] = useState(false)
  const [isDisliked, setIsDisliked] = useState(false)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  const authorText = paper.authors?.slice(0, 3).join(", ") || "Unknown authors"
  const hasMoreAuthors = (paper.authors?.length || 0) > 3
  const safeUrl = safeHref(paper.url)

  const handleSave = async () => {
    if (!onSave || isSaved) return
    setActionLoading("save")
    try {
      await onSave()
      setIsSaved(true)
    } finally {
      setActionLoading(null)
    }
  }

  const handleLike = async () => {
    if (!onLike) return
    setActionLoading("like")
    try {
      await onLike()
      setIsLiked(true)
      setIsDisliked(false)
    } finally {
      setActionLoading(null)
    }
  }

  const handleDislike = async () => {
    if (!onDislike) return
    setActionLoading("dislike")
    try {
      await onDislike()
      setIsDisliked(true)
      setIsLiked(false)
    } finally {
      setActionLoading(null)
    }
  }

  return (
    <div
      className={cn(
        "rounded-lg border bg-card p-4 space-y-3 transition-all duration-200",
        "hover:bg-accent/50 hover:shadow-sm",
        isDisliked && "opacity-60",
        className
      )}
    >
      {/* Header with title and link */}
      <div className="space-y-1">
        <div className="flex items-start justify-between gap-2">
          <h3 className="font-medium leading-snug text-base">
            {rank !== undefined && (
              <span className="text-muted-foreground mr-2">#{rank + 1}</span>
            )}
            {paper.title}
          </h3>
          {safeUrl && (
            <a
              href={safeUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="shrink-0 text-muted-foreground hover:text-foreground transition-colors"
              title="Open paper"
            >
              <ExternalLink className="h-4 w-4" />
            </a>
          )}
        </div>

        {/* Meta info */}
        <div className="text-sm text-muted-foreground flex flex-wrap items-center gap-x-1.5">
          <span className="truncate max-w-[200px] sm:max-w-none">{authorText}</span>
          {hasMoreAuthors && <span>et al.</span>}
          {paper.venue && (
            <>
              <span>·</span>
              <span className="truncate max-w-[150px] sm:max-w-none">{paper.venue}</span>
            </>
          )}
          {paper.year && (
            <>
              <span>·</span>
              <span>{paper.year}</span>
            </>
          )}
          {paper.citation_count !== undefined && paper.citation_count > 0 && (
            <>
              <span>·</span>
              <span>{paper.citation_count} citations</span>
            </>
          )}
        </div>
      </div>

      {/* Abstract preview */}
      {paper.abstract && (
        <p className="text-sm text-muted-foreground line-clamp-2 sm:line-clamp-3">
          {paper.abstract}
        </p>
      )}

      {/* Recommendation reasons */}
      {reasons && reasons.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {reasons.map((reason) => (
            <Badge key={reason} variant="outline" className="text-xs">
              {reason}
            </Badge>
          ))}
        </div>
      )}

      {/* Action buttons */}
      <div className="flex items-center gap-2 pt-1 flex-wrap">
        {onSave && (
          <Button
            size="sm"
            variant={isSaved ? "default" : "outline"}
            className={cn(
              "h-8 gap-1.5 transition-all",
              isSaved && "bg-green-600 hover:bg-green-700 text-white"
            )}
            onClick={handleSave}
            disabled={isLoading || actionLoading !== null || isSaved}
          >
            {actionLoading === "save" ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : isSaved ? (
              <Check className="h-3.5 w-3.5" />
            ) : (
              <Save className="h-3.5 w-3.5" />
            )}
            {isSaved ? "Saved" : "Save"}
          </Button>
        )}
        {onLike && (
          <Button
            size="sm"
            variant="ghost"
            className={cn(
              "h-8 gap-1.5 transition-all",
              isLiked && "text-red-500 hover:text-red-600"
            )}
            onClick={handleLike}
            disabled={isLoading || actionLoading !== null}
          >
            {actionLoading === "like" ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Heart className={cn("h-3.5 w-3.5", isLiked && "fill-current")} />
            )}
            {isLiked ? "Liked" : "Like"}
          </Button>
        )}
        {onDislike && (
          <Button
            size="sm"
            variant="ghost"
            className={cn(
              "h-8 gap-1.5 transition-all",
              isDisliked
                ? "text-orange-500 hover:text-orange-600"
                : "text-muted-foreground hover:text-destructive"
            )}
            onClick={handleDislike}
            disabled={isLoading || actionLoading !== null}
          >
            {actionLoading === "dislike" ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <ThumbsDown className={cn("h-3.5 w-3.5", isDisliked && "fill-current")} />
            )}
            {isDisliked ? "Hidden" : "Not relevant"}
          </Button>
        )}
      </div>
    </div>
  )
}
