import { fetchActivities } from "@/lib/api"
import { NewPaperCard } from "./feed/NewPaperCard"
import { MilestoneCard } from "./feed/MilestoneCard"
import { ConferenceCard } from "./feed/ConferenceCard"

export async function ActivityFeed() {
    const activities = await fetchActivities()

    return (
        <div className="space-y-3">
            <h3 className="text-sm font-semibold tracking-tight">Recent Activity</h3>
            {activities.length === 0 ? (
                <p className="text-xs text-muted-foreground py-4 text-center">
                    No recent activity. Start by searching papers or running a harvest.
                </p>
            ) : (
                <div className="space-y-2">
                    {activities.map((activity) => {
                        switch (activity.type) {
                            case "published":
                                return <NewPaperCard key={activity.id} activity={activity} />
                            case "milestone":
                                return <MilestoneCard key={activity.id} activity={activity} />
                            case "conference":
                                return <ConferenceCard key={activity.id} activity={activity} />
                            default:
                                return null
                        }
                    })}
                </div>
            )}
        </div>
    )
}
