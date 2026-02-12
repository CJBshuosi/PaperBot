import { FileText, Zap, Bookmark, CalendarClock } from "lucide-react"

interface StatsBarProps {
  papers: number
  tokens: string
  saved: number
  tracks: number
}

export function StatsBar({ papers, tokens, saved, tracks }: StatsBarProps) {
  const items = [
    { icon: FileText, label: "papers", value: papers },
    { icon: Zap, label: "tokens", value: tokens },
    { icon: Bookmark, label: "saved", value: saved },
    { icon: CalendarClock, label: "tracks", value: tracks },
  ]

  return (
    <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
      {items.map((item) => (
        <span key={item.label} className="inline-flex items-center gap-1.5">
          <item.icon className="h-3.5 w-3.5" />
          <span className="font-medium text-foreground">{item.value}</span>
          {item.label}
        </span>
      ))}
    </div>
  )
}
