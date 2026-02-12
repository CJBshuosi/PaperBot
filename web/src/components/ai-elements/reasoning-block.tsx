import { Lightbulb } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

interface ReasoningBlockProps {
  reasons: string[]
  title?: string
  compact?: boolean
  className?: string
}

export function ReasoningBlock({
  reasons,
  title = "Reasoning",
  compact = false,
  className,
}: ReasoningBlockProps) {
  if (!reasons.length) return null

  return (
    <div className={cn("rounded-md border bg-muted/20 p-2", className)}>
      <div className="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
        <Lightbulb className="h-3.5 w-3.5" />
        {title}
      </div>
      {compact ? (
        <div className="flex flex-wrap gap-1.5">
          {reasons.map((reason) => (
            <Badge key={reason} variant="outline" className="text-xs">
              {reason}
            </Badge>
          ))}
        </div>
      ) : (
        <ul className="list-disc space-y-1 pl-4 text-xs text-foreground/90">
          {reasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      )}
    </div>
  )
}
