import Link from "next/link"
import { CalendarClock, ExternalLink } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { DeadlineRadarItem } from "@/lib/types"

interface DeadlineRadarProps {
  items: DeadlineRadarItem[]
}

export function DeadlineRadar({ items }: DeadlineRadarProps) {
  return (
    <Card>
      <CardHeader className="py-3 px-4">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <CalendarClock className="h-4 w-4 text-rose-500" />
          Deadline Radar
        </CardTitle>
      </CardHeader>
      <CardContent className="px-4 py-2 space-y-1.5">
        {!items.length ? (
          <p className="text-xs text-muted-foreground">No upcoming deadlines.</p>
        ) : (
          items.slice(0, 5).map((item) => (
            <div key={`${item.name}-${item.deadline}`} className="rounded-md border p-2 space-y-1.5">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="text-sm font-medium leading-tight truncate">{item.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {item.field} · D-{item.days_left}
                  </p>
                </div>
                <Badge variant="secondary" className="text-xs shrink-0">
                  CCF {item.ccf_level}
                </Badge>
              </div>

              <div className="flex flex-wrap gap-1.5">
                {item.matched_tracks?.slice(0, 2).map((track) => (
                  <Link
                    key={`${item.name}-${track.track_id}`}
                    href={`/research?track_id=${track.track_id}`}
                    className="inline-flex"
                  >
                    <Badge variant="outline" className="text-xs hover:bg-muted cursor-pointer">
                      {track.track_name}
                    </Badge>
                  </Link>
                ))}
                {item.url && (
                  <Link
                    href={item.url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs text-muted-foreground hover:underline inline-flex items-center gap-0.5"
                  >
                    CFP <ExternalLink className="h-3 w-3" />
                  </Link>
                )}
              </div>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  )
}
