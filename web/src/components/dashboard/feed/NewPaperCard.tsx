"use client"

import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { BarChart } from "lucide-react"
import { Activity } from "@/lib/types"

interface NewPaperCardProps {
    activity: Activity
}

export function NewPaperCard({ activity }: NewPaperCardProps) {
    if (!activity.paper) return null

    return (
        <Card className="rounded-xl border shadow-sm hover:shadow-md transition-shadow">
            <CardContent className="p-5 flex flex-col gap-3">
                <div>
                    <h3 className="text-base font-semibold leading-tight">
                        {activity.paper.title}
                    </h3>
                    {activity.scholar && (
                        <p className="text-sm text-muted-foreground mt-1">
                            {activity.scholar.name}
                            {activity.paper.venue ? ` · ${activity.paper.venue}` : ""}
                            {activity.scholar.affiliation ? ` · ${activity.scholar.affiliation}` : ""}
                        </p>
                    )}
                </div>

                {activity.paper.abstract_snippet && (
                    <p className="text-sm text-muted-foreground leading-relaxed line-clamp-2">
                        {activity.paper.abstract_snippet}
                    </p>
                )}

                <div className="flex flex-wrap gap-1.5">
                    {activity.paper.venue && (
                        <Badge variant="secondary" className="rounded-full text-xs">
                            {activity.paper.venue}
                        </Badge>
                    )}
                    {activity.paper.year && (
                        <Badge variant="outline" className="rounded-full text-xs">
                            {activity.paper.year}
                        </Badge>
                    )}
                    {(activity.paper.tags || []).map((tag) => (
                        <Badge key={tag} variant="outline" className="rounded-full text-xs">
                            {tag}
                        </Badge>
                    ))}
                </div>

                <div className="flex items-center justify-between pt-1">
                    {activity.paper.citations > 0 && (
                        <div className="flex items-center gap-1.5 text-muted-foreground">
                            <BarChart className="h-3.5 w-3.5" />
                            <span className="text-xs">{activity.paper.citations} citations</span>
                        </div>
                    )}
                    <div className="text-xs text-muted-foreground">{activity.timestamp}</div>
                </div>
            </CardContent>
        </Card>
    )
}
