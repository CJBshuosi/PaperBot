"use client"

import { KeyboardEvent, useRef } from "react"
import { Loader2, Search } from "lucide-react"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"

import { TrackSelector, type Track } from "./TrackSelector"

interface SearchBoxProps {
  query: string
  onQueryChange: (query: string) => void
  onSearch: () => void
  tracks: Track[]
  activeTrack: Track | null
  onSelectTrack: (trackId: number) => void
  onNewTrack: () => void
  onManageTracks: () => void
  isSearching?: boolean
  disabled?: boolean
  placeholder?: string
  className?: string
}

export function SearchBox({
  query,
  onQueryChange,
  onSearch,
  tracks,
  activeTrack,
  onSelectTrack,
  onNewTrack,
  onManageTracks,
  isSearching = false,
  disabled = false,
  placeholder = "Search for papers on RAG, transformers, security...",
  className,
}: SearchBoxProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Submit on Enter (without Shift)
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      if (query.trim() && !isSearching && !disabled) {
        onSearch()
      }
    }
  }

  const handleSubmit = () => {
    if (query.trim() && !isSearching && !disabled) {
      onSearch()
    }
  }

  return (
    <div
      className={cn(
        "w-full",
        className
      )}
    >
      <div
        className={cn(
          "relative rounded-2xl border bg-background shadow-sm transition-all duration-200",
          "focus-within:shadow-md focus-within:border-primary/50",
          disabled && "opacity-60"
        )}
      >
        {/* Search Input */}
        <Textarea
          ref={textareaRef}
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled || isSearching}
          className={cn(
            "min-h-[70px] sm:min-h-[80px] max-h-[200px] resize-none border-0 bg-transparent",
            "px-4 sm:px-5 pt-4 sm:pt-5 pb-14",
            "text-base sm:text-lg placeholder:text-muted-foreground/60",
            "focus-visible:ring-0 focus-visible:ring-offset-0"
          )}
          rows={1}
        />

        {/* Bottom Toolbar */}
        <div className="absolute bottom-0 left-0 right-0 flex items-center justify-end px-3 sm:px-4 py-2.5 sm:py-3">
          {/* Right side - Track selector and Search button */}
          <div className="flex items-center gap-1.5 sm:gap-2">
            <TrackSelector
              tracks={tracks}
              activeTrack={activeTrack}
              onSelectTrack={onSelectTrack}
              onNewTrack={onNewTrack}
              onManageTracks={onManageTracks}
              disabled={disabled || isSearching}
            />

            <Button
              size="icon"
              className="h-9 w-9 sm:h-8 sm:w-8 rounded-lg"
              onClick={handleSubmit}
              disabled={disabled || isSearching || !query.trim()}
            >
              {isSearching ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Search className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
