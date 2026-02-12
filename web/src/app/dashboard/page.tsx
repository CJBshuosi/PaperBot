import { ActivityFeed } from "@/components/dashboard/ActivityFeed"
import { StatsCard } from "@/components/dashboard/StatsCard"
import { PipelineStatus } from "@/components/dashboard/PipelineStatus"
import { ReadingQueue } from "@/components/dashboard/ReadingQueue"
import { LLMUsageChart } from "@/components/dashboard/LLMUsageChart"
import { QuickActions } from "@/components/dashboard/QuickActions"
import { DeadlineRadar } from "@/components/dashboard/DeadlineRadar"
import { Users, FileText, Zap, BookOpen, Search, TrendingUp } from "lucide-react"
import { fetchStats, fetchTrendingTopics, fetchPipelineTasks, fetchReadingQueue, fetchLLMUsage, fetchDeadlineRadar } from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"

export default async function DashboardPage() {
  const [statsResult, trendsResult, tasksResult, readingQueueResult, llmUsageResult, deadlineResult] = await Promise.allSettled([
    fetchStats(),
    fetchTrendingTopics(),
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
  const trends = trendsResult.status === "fulfilled" ? trendsResult.value : []
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
    <div className="flex-1 p-4 space-y-3 min-h-screen">
      {/* Compact Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Hello, Researcher</h2>
          <p className="text-sm text-muted-foreground">Daily intelligence briefing</p>
        </div>
        <div className="flex w-full sm:max-w-sm items-center gap-1.5 bg-muted/50 p-1 rounded-md border">
          <Search className="ml-2 h-4 w-4 text-muted-foreground" />
          <Input
            type="text"
            placeholder="arXiv ID, URL or search..."
            className="h-8 border-none bg-transparent shadow-none focus-visible:ring-0 text-sm"
          />
          <Button size="sm" className="h-7 text-xs">Import</Button>
        </div>
      </div>

      {/* Stats Row - Compact */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
        <StatsCard title="Scholars" value={stats.tracked_scholars.toString()} description="+4" icon={Users} />
        <StatsCard title="Papers" value={stats.new_papers.toString()} description="24h" icon={FileText} />
        <StatsCard title="LLM" value={stats.llm_usage} description="tokens (window)" icon={Zap} />
        <StatsCard title="Queue" value={stats.read_later.toString()} description="to read" icon={BookOpen} />
      </div>

      {/* Main Grid - 12 Column Dense Layout */}
      <div className="grid grid-cols-12 gap-2">
        {/* Activity Feed - Main Content */}
        <div className="col-span-12 lg:col-span-8">
          <ActivityFeed />
        </div>

        {/* Right Sidebar */}
        <div className="col-span-12 lg:col-span-4 space-y-2">
          <PipelineStatus tasks={tasks} />
          <ReadingQueue items={readingQueue} />
          <DeadlineRadar items={deadlines} />
          <QuickActions />
        </div>

        {/* Bottom Row */}
        <div className="col-span-12 lg:col-span-6">
          <LLMUsageChart data={usageSummary} />
        </div>

        <Card className="col-span-12 lg:col-span-6">
          <CardHeader className="py-3 px-4">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-orange-500" /> Trending
            </CardTitle>
          </CardHeader>
          <CardContent className="py-2 px-4">
            <div className="space-y-2">
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div className="rounded-md border p-2">
                  <p className="text-muted-foreground">Calls</p>
                  <p className="font-semibold">{usageSummary.totals?.calls || 0}</p>
                </div>
                <div className="rounded-md border p-2">
                  <p className="text-muted-foreground">Tokens</p>
                  <p className="font-semibold">{(usageSummary.totals?.total_tokens || 0).toLocaleString()}</p>
                </div>
                <div className="rounded-md border p-2">
                  <p className="text-muted-foreground">Cost (USD)</p>
                  <p className="font-semibold">${Number(usageSummary.totals?.total_cost_usd || 0).toFixed(4)}</p>
                </div>
              </div>

              <div className="space-y-1">
                {(usageSummary.provider_models || []).slice(0, 6).map((row) => (
                  <div key={`${row.provider_name}-${row.model_name}`} className="flex items-center justify-between text-xs rounded border px-2 py-1">
                    <div className="min-w-0">
                      <p className="truncate font-medium">{row.provider_name} / {row.model_name}</p>
                      <p className="text-muted-foreground">calls: {row.calls}</p>
                    </div>
                    <div className="text-right">
                      <p>{row.total_tokens.toLocaleString()} tok</p>
                      <p className="text-muted-foreground">${Number(row.total_cost_usd || 0).toFixed(4)}</p>
                    </div>
                  </div>
                ))}
                {(!usageSummary.provider_models || usageSummary.provider_models.length === 0) && (
                  <div className="text-xs text-muted-foreground rounded border p-2">No usage records yet.</div>
                )}
              </div>

              <div className="flex flex-wrap gap-1.5 pt-1">
                {trends.map((topic) => (
                  <Badge
                    key={`${topic.text}-${topic.value}`}
                    variant="secondary"
                    className="text-xs cursor-pointer hover:bg-primary hover:text-primary-foreground transition-colors"
                  >
                    {topic.text}
                  </Badge>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
