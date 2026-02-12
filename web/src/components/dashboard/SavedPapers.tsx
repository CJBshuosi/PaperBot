import Link from "next/link"
import { Bookmark } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { SavedPaper } from "@/lib/types"

interface SavedPapersProps {
  items: SavedPaper[]
}

export function SavedPapers({ items }: SavedPapersProps) {
  return (
    <Card>
      <CardHeader className="py-3 px-4">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Bookmark className="h-4 w-4 text-blue-500" />
          Saved Papers
        </CardTitle>
      </CardHeader>
      <CardContent className="px-4 py-2 space-y-1">
        {!items.length ? (
          <p className="text-xs text-muted-foreground">No saved papers yet.</p>
        ) : (
          items.map((item) => (
            <Link
              key={item.id}
              href={`/papers/${item.paper_id}`}
              className="block py-1.5 border-b last:border-b-0 hover:bg-muted/50 -mx-1 px-1 rounded"
            >
              <p className="text-sm leading-tight truncate">{item.title}</p>
              <p className="text-xs text-muted-foreground truncate">{item.authors}</p>
            </Link>
          ))
        )}
      </CardContent>
    </Card>
  )
}
