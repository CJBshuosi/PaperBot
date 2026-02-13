"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { BookMarked } from "lucide-react"
import type { ReadingQueueItem } from "@/lib/types"
import Link from "next/link"

interface ReadingQueueProps {
    items: ReadingQueueItem[]
}

export function ReadingQueue({ items }: ReadingQueueProps) {
    return (
        <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 p-3 pb-2">
                <CardTitle className="text-xs font-medium flex items-center gap-1.5">
                    <BookMarked className="h-3 w-3" /> Saved Papers
                </CardTitle>
                {items.length > 0 && (
                    <Badge variant="secondary" className="text-[10px] px-1.5 py-0">{items.length}</Badge>
                )}
            </CardHeader>
            <CardContent className="p-3 pt-0 space-y-1">
                {items.length === 0 ? (
                    <p className="text-xs text-muted-foreground">No saved papers yet.</p>
                ) : (
                    items.map((item) => (
                        <Link
                            key={item.id}
                            href={`/papers/${item.paper_id}`}
                            className="block p-1.5 rounded hover:bg-muted/50 text-xs font-medium truncate"
                        >
                            {item.title}
                        </Link>
                    ))
                )}
            </CardContent>
        </Card>
    )
}
