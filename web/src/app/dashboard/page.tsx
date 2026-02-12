import { StatsBar } from "@/components/dashboard/StatsBar"
import { ActivityTimeline } from "@/components/dashboard/ActivityTimeline"
import { LLMUsageChart } from "@/components/dashboard/LLMUsageChart"
import { SavedPapers } from "@/components/dashboard/SavedPapers"
import { DeadlineRadar } from "@/components/dashboard/DeadlineRadar"
import { fetchStats, fetchActivities, fetchSavedPapers, fetchLLMUsage, fetchDeadlineRadar } from "@/lib/api"

export default async function DashboardPage() {
  const [statsResult, activitiesResult, savedResult, llmResult, deadlineResult] = await Promise.allSettled([
    fetchStats(),
    fetchActivities(),
    fetchSavedPapers(),
    fetchLLMUsage(),
    fetchDeadlineRadar("default"),
  ])

  const stats = statsResult.status === "fulfilled" ? statsResult.value : {
    tracked_scholars: 0,
    new_papers: 0,
    llm_usage: "0",
    read_later: 0,
  }
  const activities = activitiesResult.status === "fulfilled" ? activitiesResult.value : []
  const saved = savedResult.status === "fulfilled" ? savedResult.value : []
  const usageSummary = llmResult.status === "fulfilled" ? llmResult.value : {
    window_days: 7,
    daily: [],
    provider_models: [],
    totals: { calls: 0, total_tokens: 0, total_cost_usd: 0 },
  }
  const deadlines = deadlineResult.status === "fulfilled" ? deadlineResult.value : []

  const today = new Date().toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  })

  return (
    <div className="flex-1 p-4 space-y-3 min-h-screen">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-2">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Welcome back</h2>
          <StatsBar
            papers={stats.new_papers}
            tokens={stats.llm_usage}
            saved={stats.read_later}
            tracks={deadlines.length}
          />
        </div>
        <p className="text-sm text-muted-foreground">{today}</p>
      </div>

      {/* Main Grid: 2/3 + 1/3 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        {/* Left: Activity Timeline */}
        <div className="lg:col-span-2">
          <ActivityTimeline items={activities} />
        </div>

        {/* Right: stacked cards */}
        <div className="space-y-3">
          <LLMUsageChart data={usageSummary} />
          <SavedPapers items={saved} />
          <DeadlineRadar items={deadlines} />
        </div>
      </div>
    </div>
  )
}
