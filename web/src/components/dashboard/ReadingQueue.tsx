"use client"

import Link from "next/link"
import { BookMarked, Clock3 } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { ReadingQueueItem } from "@/lib/types"

interface ReadingQueueProps {
  items: ReadingQueueItem[]
}

export function ReadingQueue({ items }: ReadingQueueProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 p-4 pb-3">
        <CardTitle className="text-sm font-medium flex items-center gap-1.5">
          <BookMarked className="h-4 w-4 text-blue-500" />
          Reading Queue
        </CardTitle>
        <Badge variant="secondary" className="h-5 px-1.5 text-xs">
          {items.length}
        </Badge>
      </CardHeader>
      <CardContent className="space-y-2 p-4 pt-0">
        {items.length === 0 ? (
          <p className="text-xs text-muted-foreground">No saved papers yet. Save papers from Research or Library.</p>
        ) : (
          <>
            {items.slice(0, 6).map((item) => (
              <Link
                key={item.id}
                href={`/papers/${item.paper_id}`}
                className="block rounded-lg border p-2.5 transition hover:border-primary/40 hover:bg-muted/40"
              >
                <p className="line-clamp-2 text-sm font-medium leading-snug">{item.title}</p>
                <p className="mt-1 line-clamp-1 text-xs text-muted-foreground">
                  {item.authors || "Unknown authors"}
                </p>
                {item.saved_at ? (
                  <p className="mt-1 inline-flex items-center gap-1 text-[11px] text-muted-foreground">
                    <Clock3 className="h-3 w-3" />
                    saved {new Date(item.saved_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                  </p>
                ) : null}
              </Link>
            ))}
            <Button asChild variant="ghost" size="sm" className="w-full justify-start px-1">
              <Link href="/papers">Open full library</Link>
            </Button>
          </>
        )}
      </CardContent>
    </Card>
  )
}
