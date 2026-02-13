import { ActivityFeed } from "@/components/dashboard/ActivityFeed"
import { StatsCard } from "@/components/dashboard/StatsCard"
import { PipelineStatus } from "@/components/dashboard/PipelineStatus"
import { ReadingQueue } from "@/components/dashboard/ReadingQueue"
import { LLMUsageChart } from "@/components/dashboard/LLMUsageChart"
import { QuickActions } from "@/components/dashboard/QuickActions"
import { DeadlineRadar } from "@/components/dashboard/DeadlineRadar"
import { Users, FileText, Zap, BookOpen } from "lucide-react"
import { fetchStats, fetchPipelineTasks, fetchReadingQueue, fetchLLMUsage, fetchDeadlineRadar } from "@/lib/api"

export default async function DashboardPage() {
  const [statsResult, tasksResult, readingQueueResult, llmUsageResult, deadlineResult] = await Promise.allSettled([
    fetchStats(),
    fetchPipelineTasks(),
    fetchReadingQueue(),
    fetchLLMUsage(),
    fetchDeadlineRadar("default"),
  ])
  const stats = statsResult.status === "fulfilled" ? statsResult.value : {
    tracked_scholars: 0,
    new_papers: 0,
    llm_usage: "0",
    read_later: 0,
  }
  const tasks = tasksResult.status === "fulfilled" ? tasksResult.value : []
  const readingQueue = readingQueueResult.status === "fulfilled" ? readingQueueResult.value : []
  const usageSummary = llmUsageResult.status === "fulfilled" ? llmUsageResult.value : {
    window_days: 7,
    daily: [],
    provider_models: [],
    totals: { calls: 0, total_tokens: 0, total_cost_usd: 0 },
  }
  const deadlines = deadlineResult.status === "fulfilled" ? deadlineResult.value : []

  return (
    <div className="flex-1 p-4 space-y-4 min-h-screen max-w-7xl mx-auto">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Dashboard</h2>
        <p className="text-sm text-muted-foreground">Overview of your research workspace</p>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatsCard title="Scholars" value={stats.tracked_scholars.toString()} description="tracked" icon={Users} />
        <StatsCard title="Papers" value={stats.new_papers.toString()} description="in library" icon={FileText} />
        <StatsCard title="LLM" value={stats.llm_usage} description="tokens" icon={Zap} />
        <StatsCard title="Saved" value={stats.read_later.toString()} description="to read" icon={BookOpen} />
      </div>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Left: Activity Feed + LLM Usage */}
        <div className="lg:col-span-2 space-y-4">
          <ActivityFeed />
          <LLMUsageChart data={usageSummary} />
        </div>

        {/* Right sidebar */}
        <div className="space-y-4">
          <QuickActions />
          <PipelineStatus tasks={tasks} />
          <ReadingQueue items={readingQueue} />
          <DeadlineRadar items={deadlines} />
        </div>
      </div>
    </div>
  )
}