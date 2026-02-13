"use client"

import { Card, CardContent } from "@/components/ui/card"
import { CalendarClock, MapPin } from "lucide-react"
import { Activity } from "@/lib/types"

interface ConferenceCardProps {
    activity: Activity
}

export function ConferenceCard({ activity }: ConferenceCardProps) {
    if (!activity.conference) return null

    return (
        <Card>
            <CardContent className="p-5">
                <div className="flex gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400 shrink-0">
                        <CalendarClock className="h-5 w-5" />
                    </div>
                    <div className="flex-1 space-y-1">
                        <h4 className="font-semibold text-sm">
                            {activity.conference.name}
                        </h4>
                        <div className="text-xs text-muted-foreground flex items-center gap-1.5">
                            <MapPin className="h-3 w-3" />
                            {activity.conference.location}
                            <span>·</span>
                            <span>{activity.conference.date}</span>
                        </div>
                        {activity.conference.deadline_countdown && (
                            <p className="text-xs font-medium text-orange-600 dark:text-orange-400 pt-1">
                                Deadline in {activity.conference.deadline_countdown}
                            </p>
                        )}
                    </div>
                </div>
            </CardContent>
        </Card>
    )
}
