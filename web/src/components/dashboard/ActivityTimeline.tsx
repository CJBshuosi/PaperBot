import { FileText, Bookmark, Layers } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { TimelineItem } from "@/lib/types"

interface ActivityTimelineProps {
  items: TimelineItem[]
}

const kindIcon = {
  harvest: FileText,
  save: Bookmark,
  note: Layers,
} as const

export function ActivityTimeline({ items }: ActivityTimelineProps) {
  return (
    <Card className="h-full">
      <CardHeader className="py-3 px-4">
        <CardTitle className="text-sm font-medium">Recent Activity</CardTitle>
      </CardHeader>
      <CardContent className="px-4 py-2 space-y-1">
        {!items.length ? (
          <p className="text-xs text-muted-foreground py-4">No recent activity.</p>
        ) : (
          items.map((item) => {
            const Icon = kindIcon[item.kind] || FileText
            return (
              <div
                key={item.id}
                className="flex items-start gap-2.5 py-1.5 border-b last:border-b-0"
              >
                <Icon className="h-3.5 w-3.5 mt-0.5 shrink-0 text-muted-foreground" />
                <div className="min-w-0 flex-1">
                  <p className="text-sm leading-tight truncate">{item.title}</p>
                  {item.subtitle && (
                    <p className="text-xs text-muted-foreground truncate">{item.subtitle}</p>
                  )}
                </div>
                <span className="text-xs text-muted-foreground shrink-0">{item.timestamp}</span>
              </div>
            )
          })
        )}
      </CardContent>
    </Card>
  )
}
