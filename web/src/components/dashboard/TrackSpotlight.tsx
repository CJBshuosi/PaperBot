import Link from "next/link"
import { ArrowRight, Bookmark, Compass, Hash, Sparkles, Star } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { AnchorPreviewItem, ResearchTrackSummary, TrackFeedItem } from "@/lib/types"

interface TrackSpotlightProps {
  track: ResearchTrackSummary | null
  feedItems: TrackFeedItem[]
  feedTotal: number
  anchors: AnchorPreviewItem[]
}

function toPaperHref(item: TrackFeedItem): string {
  return `/papers/${encodeURIComponent(String(item.paper?.id || ""))}`
}

function formatScore(score?: number): string {
  if (typeof score !== "number" || Number.isNaN(score)) return "0.0"
  return score.toFixed(1)
}

export function TrackSpotlight({ track, feedItems, feedTotal, anchors }: TrackSpotlightProps) {
  if (!track) {
    return (
      <Card className="border-dashed">
        <CardHeader>
          <CardTitle className="text-base">Track Spotlight</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">
            No active track yet. Create one to unlock personalized feed, anchor authors, and memory routing.
          </p>
          <Button asChild size="sm">
            <Link href="/research">Open Research Workspace</Link>
          </Button>
        </CardContent>
      </Card>
    )
  }

  const keywords = (track.keywords || []).slice(0, 6)

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              <Compass className="h-4 w-4 text-primary" />
              Track Spotlight · {track.name}
            </CardTitle>
            <p className="mt-1 text-xs text-muted-foreground">
              {track.description || "Track-level feed blending keyword match, feedback preference and judge score."}
            </p>
          </div>
          <Button asChild variant="outline" size="sm">
            <Link href={`/research?track_id=${track.id}`}>Open Track</Link>
          </Button>
        </div>
        {!!keywords.length && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {keywords.map((keyword) => (
              <Badge key={keyword} variant="secondary" className="text-xs">
                <Hash className="mr-1 h-3 w-3" />
                {keyword}
              </Badge>
            ))}
          </div>
        )}
      </CardHeader>

      <CardContent className="grid gap-4 xl:grid-cols-5">
        <div className="space-y-2 xl:col-span-3">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium">Feed Candidates</p>
            <span className="text-xs text-muted-foreground">{feedTotal} total</span>
          </div>

          {!feedItems.length ? (
            <p className="rounded-lg border border-dashed p-3 text-xs text-muted-foreground">
              No feed items yet. Run a search from Research to populate the track feed.
            </p>
          ) : (
            <div className="space-y-2">
              {feedItems.slice(0, 5).map((item) => (
                <Link
                  key={`${item.paper.id}-${item.feed_score}`}
                  href={toPaperHref(item)}
                  className="block rounded-lg border p-3 transition hover:border-primary/40 hover:bg-muted/40"
                >
                  <p className="line-clamp-2 text-sm font-medium leading-snug">{item.paper.title}</p>
                  <div className="mt-1 flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
                    {item.paper.venue ? <span>{item.paper.venue}</span> : null}
                    {item.paper.year ? <span>· {item.paper.year}</span> : null}
                    <Badge variant="outline" className="h-5 px-1.5">
                      score {formatScore(item.feed_score)}
                    </Badge>
                    {item.latest_feedback_action ? (
                      <Badge variant="secondary" className="h-5 px-1.5 capitalize">
                        {item.latest_feedback_action}
                      </Badge>
                    ) : null}
                  </div>
                </Link>
              ))}
            </div>
          )}

          <Button asChild variant="ghost" size="sm" className="px-0">
            <Link href={`/research?track_id=${track.id}`}>
              View full feed
              <ArrowRight className="ml-1 h-3.5 w-3.5" />
            </Link>
          </Button>
        </div>

        <div className="space-y-2 xl:col-span-2">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium flex items-center gap-1.5">
              <Sparkles className="h-4 w-4 text-yellow-500" />
              Anchor Authors
            </p>
            <span className="text-xs text-muted-foreground">Top {anchors.length || 0}</span>
          </div>

          {!anchors.length ? (
            <p className="rounded-lg border border-dashed p-3 text-xs text-muted-foreground">
              Anchor discovery is empty for this track right now.
            </p>
          ) : (
            <div className="space-y-2">
              {anchors.map((anchor) => (
                <div key={anchor.author_id} className="rounded-lg border p-3">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm font-medium truncate">{anchor.name}</p>
                    <Badge variant="outline" className="h-5 px-1.5">
                      <Star className="mr-1 h-3 w-3" />
                      {formatScore(anchor.anchor_score)}
                    </Badge>
                  </div>
                  <div className="mt-1 flex items-center gap-1.5 text-xs text-muted-foreground">
                    <span className="capitalize">{anchor.anchor_level || "candidate"}</span>
                    {anchor.user_action ? (
                      <Badge variant="secondary" className="h-5 px-1.5 capitalize">
                        <Bookmark className="mr-1 h-3 w-3" />
                        {anchor.user_action}
                      </Badge>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
