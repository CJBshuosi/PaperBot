"use client"

import { Card, CardContent } from "@/components/ui/card"
import { TrendingUp, TrendingDown, Minus } from "lucide-react"
import { Activity } from "@/lib/types"

interface MilestoneCardProps {
    activity: Activity
}

const trendIcons = {
    up: <TrendingUp className="h-4 w-4 text-green-500" />,
    down: <TrendingDown className="h-4 w-4 text-red-500" />,
    flat: <Minus className="h-4 w-4 text-muted-foreground" />,
}

export function MilestoneCard({ activity }: MilestoneCardProps) {
    if (!activity.milestone) return null

    const trend = activity.milestone.trend || "flat"

    return (
        <Card>
            <CardContent className="p-5">
                <div className="flex items-start justify-between gap-3">
                    <div className="space-y-1">
                        <h4 className="font-semibold text-sm">{activity.milestone.title}</h4>
                        <p className="text-xs text-muted-foreground">
                            {activity.milestone.description}
                        </p>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                        {trendIcons[trend as keyof typeof trendIcons] || trendIcons.flat}
                        {activity.milestone.current_value != null && (
                            <span className="text-sm font-medium">{activity.milestone.current_value}</span>
                        )}
                    </div>
                </div>
                <div className="text-xs text-muted-foreground mt-2">{activity.timestamp}</div>
            </CardContent>
        </Card>
    )
}
