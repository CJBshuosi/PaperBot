"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import Markdown from "react-markdown"
import remarkGfm from "remark-gfm"
import {
  BookOpenIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  FilterIcon,
  Loader2Icon,
  MailIcon,
  PlusIcon,
  PlayIcon,
  SettingsIcon,
  SparklesIcon,
  StarIcon,
  Trash2Icon,
  TrendingUpIcon,
  XIcon,
  ZapIcon,
} from "lucide-react"

import JudgeRadarChart from "@/components/research/JudgeRadarChart"
import WorkflowDagView from "@/components/research/WorkflowDagView"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Progress } from "@/components/ui/progress"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { readSSE } from "@/lib/sse"
import { useWorkflowStore } from "@/lib/stores/workflow-store"
import type { DailyResult, WorkflowPhase } from "@/lib/stores/workflow-store"

/* ── Types (local to component) ───────────────────────── */

type DimensionScore = { score?: number; rationale?: string }

type JudgeResult = {
  relevance?: DimensionScore
  novelty?: DimensionScore
  rigor?: DimensionScore
  impact?: DimensionScore
  clarity?: DimensionScore
  overall?: number
  recommendation?: string
  one_line_summary?: string
  judge_model?: string
  judge_cost_tier?: number
}

type SearchItem = {
  title: string
  url?: string
  score?: number
  matched_queries?: string[]
  branches?: string[]
  sources?: string[]
  ai_summary?: string
  relevance?: { score?: number; reason?: string }
  judge?: JudgeResult
}

type RepoRow = {
  title: string
  query?: string
  paper_url?: string
  repo_url: string
  github?: {
    ok?: boolean
    stars?: number
    language?: string
    updated_at?: string
    error?: string
  }
}

type StepStatus = "pending" | "running" | "done" | "error" | "skipped"

/* ── Helpers ──────────────────────────────────────────── */

const DEFAULT_QUERIES = ["ICL压缩", "ICL隐式偏置", "KV Cache加速"]

const REC_COLORS: Record<string, string> = {
  must_read: "bg-green-100 text-green-800 border-green-300",
  worth_reading: "bg-blue-100 text-blue-800 border-blue-300",
  skim: "bg-yellow-100 text-yellow-800 border-yellow-300",
  skip: "bg-slate-100 text-slate-600 border-slate-300",
}

const REC_LABELS: Record<string, string> = {
  must_read: "Must Read",
  worth_reading: "Worth Reading",
  skim: "Skim",
  skip: "Skip",
}

function ScoreBar({ value, max = 5, label }: { value: number; max?: number; label: string }) {
  const pct = Math.round((value / max) * 100)
  const color = value >= 4 ? "bg-green-500" : value >= 3 ? "bg-blue-500" : value >= 2 ? "bg-yellow-500" : "bg-red-400"
  return (
    <div className="flex items-center gap-2 text-xs">
      {label && <span className="w-10 shrink-0 text-muted-foreground">{label}</span>}
      <div className="relative h-1.5 flex-1 rounded-full bg-muted">
        <div className={`absolute inset-y-0 left-0 rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-4 text-right font-mono text-muted-foreground">{value}</span>
    </div>
  )
}

function StatCard({ label, value, icon }: { label: string; value: string | number; icon: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3 rounded-lg border bg-card px-4 py-3">
      <div className="flex size-9 items-center justify-center rounded-md bg-primary/10 text-primary">{icon}</div>
      <div>
        <div className="text-2xl font-bold tabular-nums">{value}</div>
        <div className="text-xs text-muted-foreground">{label}</div>
      </div>
    </div>
  )
}

function buildDagStatuses(args: {
  phase: WorkflowPhase
  hasError: boolean
  llmIntent: boolean
  judgeIntent: boolean
  hasSearchData: boolean
  hasReportData: boolean
  hasLLMData: boolean
  hasJudgeData: boolean
  schedulerDone: boolean
}): Record<string, StepStatus> {
  const {
    phase,
    hasError,
    llmIntent,
    judgeIntent,
    hasSearchData,
    hasReportData,
    hasLLMData,
    hasJudgeData,
    schedulerDone,
  } = args

  const statuses: Record<string, StepStatus> = {
    source: hasSearchData ? "done" : "pending",
    normalize: hasSearchData ? "done" : "pending",
    search: hasSearchData ? "done" : "pending",
    rank: hasSearchData ? "done" : "pending",
    llm: "pending",
    judge: "pending",
    report: hasReportData ? "done" : "pending",
    scheduler: schedulerDone ? "done" : "pending",
  }

  if (phase === "searching") {
    statuses.source = "done"
    statuses.normalize = "done"
    statuses.search = "running"
    statuses.rank = "running"
  }

  if (phase === "reporting") {
    statuses.source = "done"
    statuses.normalize = "done"
    statuses.search = "done"
    statuses.rank = "done"
    statuses.report = "running"
  }

  if (hasLLMData) {
    statuses.llm = "done"
  } else if (phase === "reporting" && llmIntent) {
    statuses.llm = "running"
  } else if (hasReportData) {
    statuses.llm = "skipped"
  }

  if (hasJudgeData) {
    statuses.judge = "done"
  } else if (phase === "reporting" && judgeIntent) {
    statuses.judge = "running"
  } else if (hasReportData) {
    statuses.judge = "skipped"
  }

  if (phase === "error" || hasError) {
    if (!hasSearchData) {
      statuses.search = "error"
      statuses.rank = "error"
    }
    if (!hasReportData) {
      statuses.report = "error"
    }
    if (llmIntent && !hasLLMData) statuses.llm = "error"
    if (judgeIntent && !hasJudgeData) statuses.judge = "error"
  }

  return statuses
}

/* ── Stream Progress ─────────────────────────────────── */

type StreamPhase = "idle" | "search" | "build" | "llm" | "insight" | "judge" | "filter" | "save" | "notify" | "done" | "error"

const PHASE_LABELS: Record<StreamPhase, string> = {
  idle: "Idle",
  search: "Searching papers",
  build: "Building report",
  llm: "LLM enrichment",
  insight: "Generating insights",
  judge: "Judge scoring",
  filter: "Filtering papers",
  save: "Saving",
  notify: "Sending notifications",
  done: "Done",
  error: "Error",
}

const PHASE_ORDER: StreamPhase[] = ["search", "build", "llm", "insight", "judge", "filter", "save", "notify", "done"]

function StreamProgressCard({
  streamPhase,
  streamLog,
  streamProgress,
  startTime,
}: {
  streamPhase: StreamPhase
  streamLog: string[]
  streamProgress: { done: number; total: number }
  startTime: number | null
}) {
  const elapsed = startTime ? Math.round((Date.now() - startTime) / 1000) : 0
  const currentIdx = PHASE_ORDER.indexOf(streamPhase)
  const pct = streamProgress.total > 0
    ? Math.round((streamProgress.done / streamProgress.total) * 100)
    : currentIdx >= 0
      ? Math.round(((currentIdx + 0.5) / PHASE_ORDER.length) * 100)
      : 0

  return (
    <Card className="border-blue-200 bg-blue-50/40">
      <CardContent className="space-y-3 py-3">
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-2 font-medium text-blue-900">
            <Loader2Icon className="size-4 animate-spin" />
            {PHASE_LABELS[streamPhase] || streamPhase}
          </div>
          <div className="flex items-center gap-3 text-xs text-blue-700">
            {streamProgress.total > 0 && (
              <span>{streamProgress.done}/{streamProgress.total}</span>
            )}
            {elapsed > 0 && <span>{elapsed}s</span>}
          </div>
        </div>
        <Progress value={pct} />
        <div className="flex items-center gap-1.5">
          {PHASE_ORDER.slice(0, -1).map((p) => {
            const idx = PHASE_ORDER.indexOf(p)
            const status = idx < currentIdx ? "done" : idx === currentIdx ? "active" : "pending"
            return (
              <div key={p} className="flex items-center gap-1">
                <div
                  className={`size-2 rounded-full ${
                    status === "done"
                      ? "bg-green-500"
                      : status === "active"
                        ? "bg-blue-500 animate-pulse"
                        : "bg-slate-200"
                  }`}
                />
                <span className={`text-[10px] ${status === "active" ? "font-medium text-blue-900" : "text-muted-foreground"}`}>
                  {PHASE_LABELS[p]}
                </span>
              </div>
            )
          })}
        </div>
        {streamLog.length > 0 && (
          <ScrollArea className="h-32">
            <div className="space-y-0.5 font-mono text-[11px] text-muted-foreground">
              {streamLog.slice(-20).map((line, idx) => (
                <div key={`sp-${idx}`}>{line}</div>
              ))}
            </div>
          </ScrollArea>
        )}
      </CardContent>
    </Card>
  )
}

/* ── Paper Card ───────────────────────────────────────── */

function PaperCard({ item, query, onOpenDetail }: { item: SearchItem; query?: string; onOpenDetail: (item: SearchItem) => void }) {
  const judge = item.judge
  const rec = judge?.recommendation || ""
  const overall = judge?.overall ?? 0

  return (
    <div className="group cursor-pointer rounded-lg border bg-card p-4 transition-all hover:border-primary/40 hover:shadow-md" onClick={() => onOpenDetail(item)}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h4 className="line-clamp-2 text-sm font-semibold leading-snug">
            {item.url ? (
              <a href={item.url} target="_blank" rel="noreferrer" className="hover:text-primary hover:underline" onClick={(e) => e.stopPropagation()}>
                {item.title}
              </a>
            ) : (
              item.title
            )}
          </h4>
          <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
            {query && <Badge variant="outline" className="text-[10px]">{query}</Badge>}
            {(item.branches || []).map((b) => (<Badge key={b} variant="secondary" className="text-[10px]">{b}</Badge>))}
            {item.score != null && <span className="text-[10px] text-muted-foreground">score {item.score.toFixed(1)}</span>}
          </div>
        </div>
        {judge && overall > 0 && (
          <div className="flex shrink-0 flex-col items-end gap-1">
            <div className="flex size-10 items-center justify-center rounded-full border-2 border-primary/30 bg-primary/5 text-sm font-bold text-primary">{overall.toFixed(1)}</div>
            {rec && <Badge variant="outline" className={`text-[10px] ${REC_COLORS[rec] || ""}`}>{REC_LABELS[rec] || rec}</Badge>}
          </div>
        )}
      </div>
      {judge && overall > 0 && (
        <div className="mt-3 grid gap-1">
          <ScoreBar value={judge.relevance?.score ?? 0} label="Rel" />
          <ScoreBar value={judge.novelty?.score ?? 0} label="Nov" />
          <ScoreBar value={judge.rigor?.score ?? 0} label="Rig" />
          <ScoreBar value={judge.impact?.score ?? 0} label="Imp" />
          <ScoreBar value={judge.clarity?.score ?? 0} label="Clr" />
        </div>
      )}
      {judge?.one_line_summary && <p className="mt-2 text-xs italic text-muted-foreground line-clamp-2">{judge.one_line_summary}</p>}
      <div className="mt-2 flex items-center justify-end text-[10px] text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100">
        Click for details <ChevronRightIcon className="ml-0.5 size-3" />
      </div>
    </div>
  )
}

/* ── Paper Detail Dialog ──────────────────────────────── */

function PaperDetailDialog({ item, open, onClose }: { item: SearchItem | null; open: boolean; onClose: () => void }) {
  if (!item) return null
  const judge = item.judge
  const dims: Array<{ key: string; label: string; dim?: DimensionScore }> = [
    { key: "relevance", label: "Relevance", dim: judge?.relevance },
    { key: "novelty", label: "Novelty", dim: judge?.novelty },
    { key: "rigor", label: "Technical Rigor", dim: judge?.rigor },
    { key: "impact", label: "Impact Potential", dim: judge?.impact },
    { key: "clarity", label: "Clarity", dim: judge?.clarity },
  ]

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-base leading-snug pr-8">{item.title}</DialogTitle>
        </DialogHeader>
        {item.url && <a href={item.url} target="_blank" rel="noreferrer" className="text-xs text-primary hover:underline">{item.url}</a>}
        <div className="flex flex-wrap gap-1.5 mt-1">
          {(item.matched_queries || []).map((q) => (<Badge key={q} variant="outline" className="text-[10px]">{q}</Badge>))}
          {(item.branches || []).map((b) => (<Badge key={b} variant="secondary" className="text-[10px]">{b}</Badge>))}
          {item.score != null && <Badge variant="secondary" className="text-[10px]">score {item.score.toFixed(1)}</Badge>}
        </div>
        {judge && (judge.overall ?? 0) > 0 && (
          <>
            <Separator />
            <div className="grid gap-4 md:grid-cols-[200px_1fr]">
              <div>
                <JudgeRadarChart judge={judge} />
                <div className="mt-1 text-center">
                  <span className="text-2xl font-bold text-primary">{judge.overall?.toFixed(2)}</span>
                  <span className="text-sm text-muted-foreground"> / 5.0</span>
                </div>
                {judge.recommendation && <div className="mt-1 text-center"><Badge className={REC_COLORS[judge.recommendation] || ""}>{REC_LABELS[judge.recommendation] || judge.recommendation}</Badge></div>}
                {judge.judge_model && <p className="mt-2 text-center text-[10px] text-muted-foreground">Model: {judge.judge_model}</p>}
              </div>
              <div className="space-y-3">
                {judge.one_line_summary && (
                  <div className="rounded-md bg-muted/50 p-3">
                    <p className="text-sm font-medium">Summary</p>
                    <p className="mt-1 text-sm text-muted-foreground">{judge.one_line_summary}</p>
                  </div>
                )}
                {dims.map(({ key, label, dim }) => (
                  <div key={key} className="space-y-1">
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-medium">{label}</span>
                      <span className="font-mono text-muted-foreground">{dim?.score ?? "-"}/5</span>
                    </div>
                    <ScoreBar value={dim?.score ?? 0} label="" />
                    {dim?.rationale && <p className="text-xs text-muted-foreground">{dim.rationale}</p>}
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
        {item.ai_summary && (
          <>
            <Separator />
            <div>
              <p className="text-sm font-medium">AI Summary</p>
              <p className="mt-1 text-sm text-muted-foreground">{item.ai_summary}</p>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}

/* ── Config Sheet ─────────────────────────────────────── */

function ConfigSheetBody(props: {
  queryItems: string[]; setQueryItems: (v: string[]) => void
  topK: number; setTopK: (v: number) => void
  topN: number; setTopN: (v: number) => void
  showPerBranch: number; setShowPerBranch: (v: number) => void
  saveDaily: boolean; setSaveDaily: (v: boolean) => void
  outputDir: string; setOutputDir: (v: string) => void
  useArxiv: boolean; setUseArxiv: (v: boolean) => void
  useVenue: boolean; setUseVenue: (v: boolean) => void
  usePapersCool: boolean; setUsePapersCool: (v: boolean) => void
  useArxivApi: boolean; setUseArxivApi: (v: boolean) => void
  useHFDaily: boolean; setUseHFDaily: (v: boolean) => void
  enableLLM: boolean; setEnableLLM: (v: boolean) => void
  useSummary: boolean; setUseSummary: (v: boolean) => void
  useTrends: boolean; setUseTrends: (v: boolean) => void
  useInsight: boolean; setUseInsight: (v: boolean) => void
  useRelevance: boolean; setUseRelevance: (v: boolean) => void
  enableJudge: boolean; setEnableJudge: (v: boolean) => void
  judgeRuns: number; setJudgeRuns: (v: number) => void
  judgeMaxItems: number; setJudgeMaxItems: (v: number) => void
  judgeTokenBudget: number; setJudgeTokenBudget: (v: number) => void
  notifyEmail: string; setNotifyEmail: (v: string) => void
  notifyEnabled: boolean; setNotifyEnabled: (v: boolean) => void
  resendEnabled: boolean; setResendEnabled: (v: boolean) => void
}) {
  const {
    queryItems, setQueryItems, topK, setTopK, topN, setTopN,
    showPerBranch, setShowPerBranch, saveDaily, setSaveDaily,
    outputDir, setOutputDir, useArxiv, setUseArxiv, useVenue, setUseVenue,
    usePapersCool, setUsePapersCool, useArxivApi, setUseArxivApi, useHFDaily, setUseHFDaily, enableLLM, setEnableLLM,
    useSummary, setUseSummary, useTrends, setUseTrends,
    useInsight, setUseInsight, useRelevance, setUseRelevance,
    enableJudge, setEnableJudge, judgeRuns, setJudgeRuns,
    judgeMaxItems, setJudgeMaxItems, judgeTokenBudget, setJudgeTokenBudget,
    notifyEmail, setNotifyEmail, notifyEnabled, setNotifyEnabled,
    resendEnabled, setResendEnabled,
  } = props

  const updateQuery = (idx: number, value: string) => {
    const next = [...queryItems]
    next[idx] = value
    setQueryItems(next)
  }
  const removeQuery = (idx: number) => {
    if (queryItems.length <= 1) return
    setQueryItems(queryItems.filter((_, i) => i !== idx))
  }
  const addQuery = () => setQueryItems([...queryItems, ""])

  return (
    <div className="space-y-5 pr-2">
      <section className="space-y-2">
          <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Topics</Label>
          <div className="space-y-1.5">
            {queryItems.map((q, idx) => (
              <div key={idx} className="flex items-center gap-1.5">
                <Input
                  value={q}
                  onChange={(e) => updateQuery(idx, e.target.value)}
                  placeholder="Enter a topic..."
                  className="h-8 text-sm"
                />
                {queryItems.length > 1 && (
                  <Button variant="ghost" size="icon" className="size-8 shrink-0 text-muted-foreground hover:text-destructive" onClick={() => removeQuery(idx)}>
                    <XIcon className="size-3.5" />
                  </Button>
                )}
              </div>
            ))}
          </div>
          <Button variant="outline" size="sm" className="h-7 gap-1 text-xs" onClick={addQuery}>
            <PlusIcon className="size-3.5" /> Add Topic
          </Button>
        </section>

        <section className="space-y-2">
          <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Sources &amp; Branches</Label>
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-1.5 text-sm"><Checkbox checked={usePapersCool} onCheckedChange={(v) => setUsePapersCool(Boolean(v))} /> papers.cool</label>
            <label className="flex items-center gap-1.5 text-sm"><Checkbox checked={useArxivApi} onCheckedChange={(v) => setUseArxivApi(Boolean(v))} /> arXiv API</label>
            <label className="flex items-center gap-1.5 text-sm"><Checkbox checked={useHFDaily} onCheckedChange={(v) => setUseHFDaily(Boolean(v))} /> HF Daily</label>
          </div>
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-1.5 text-sm"><Checkbox checked={useArxiv} onCheckedChange={(v) => setUseArxiv(Boolean(v))} /> arxiv</label>
            <label className="flex items-center gap-1.5 text-sm"><Checkbox checked={useVenue} onCheckedChange={(v) => setUseVenue(Boolean(v))} /> venue</label>
          </div>
        </section>

        <section className="space-y-2">
          <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Parameters</Label>
          <div className="grid grid-cols-3 gap-2">
            <div className="space-y-1"><Label className="text-xs">Top K</Label><Input type="number" min={1} value={topK} onChange={(e) => setTopK(Number(e.target.value || 5))} className="h-8 text-sm" /></div>
            <div className="space-y-1"><Label className="text-xs">Show / Branch</Label><Input type="number" min={1} value={showPerBranch} onChange={(e) => setShowPerBranch(Number(e.target.value || 25))} className="h-8 text-sm" /></div>
            <div className="space-y-1"><Label className="text-xs">Daily Top N</Label><Input type="number" min={1} value={topN} onChange={(e) => setTopN(Number(e.target.value || 10))} className="h-8 text-sm" /></div>
          </div>
        </section>

        <section className="space-y-2">
          <label className="flex items-center gap-2 text-sm"><Checkbox checked={saveDaily} onCheckedChange={(v) => setSaveDaily(Boolean(v))} /> Save DailyPaper files</label>
          {saveDaily && <Input value={outputDir} onChange={(e) => setOutputDir(e.target.value)} placeholder="./reports/dailypaper" className="h-8 text-sm" />}
        </section>

        <Separator />

        <section className="space-y-2">
          <label className="flex items-center gap-2 text-sm font-medium">
            <Checkbox checked={enableLLM} onCheckedChange={(v) => setEnableLLM(Boolean(v))} />
            <SparklesIcon className="size-4" /> LLM Analysis
          </label>
          {enableLLM && (
            <div className="ml-6 grid grid-cols-2 gap-2 text-sm">
              <label className="flex items-center gap-1.5"><Checkbox checked={useSummary} onCheckedChange={(v) => setUseSummary(Boolean(v))} /> Summary</label>
              <label className="flex items-center gap-1.5"><Checkbox checked={useTrends} onCheckedChange={(v) => setUseTrends(Boolean(v))} /> Trends</label>
              <label className="flex items-center gap-1.5"><Checkbox checked={useInsight} onCheckedChange={(v) => setUseInsight(Boolean(v))} /> Insight</label>
              <label className="flex items-center gap-1.5"><Checkbox checked={useRelevance} onCheckedChange={(v) => setUseRelevance(Boolean(v))} /> Relevance</label>
            </div>
          )}
        </section>

        <section className="space-y-2">
          <label className="flex items-center gap-2 text-sm font-medium">
            <Checkbox checked={enableJudge} onCheckedChange={(v) => setEnableJudge(Boolean(v))} />
            <StarIcon className="size-4" /> LLM Judge
          </label>
          {enableJudge && (
            <div className="ml-6 grid grid-cols-3 gap-2">
              <div className="space-y-1"><Label className="text-xs">Runs</Label><Input type="number" min={1} max={5} value={judgeRuns} onChange={(e) => setJudgeRuns(Number(e.target.value || 1))} className="h-8 text-sm" /></div>
              <div className="space-y-1"><Label className="text-xs">Max Items</Label><Input type="number" min={1} max={200} value={judgeMaxItems} onChange={(e) => setJudgeMaxItems(Number(e.target.value || 20))} className="h-8 text-sm" /></div>
              <div className="space-y-1"><Label className="text-xs">Token Budget</Label><Input type="number" min={0} value={judgeTokenBudget} onChange={(e) => setJudgeTokenBudget(Number(e.target.value || 0))} className="h-8 text-sm" /></div>
            </div>
          )}
        </section>

        <Separator />

        <section className="space-y-2">
          <label className="flex items-center gap-2 text-sm font-medium">
            <Checkbox checked={notifyEnabled} onCheckedChange={(v) => setNotifyEnabled(Boolean(v))} />
            <MailIcon className="size-4" /> Email Notification
          </label>
          {notifyEnabled && (
            <div className="ml-6 space-y-2">
              <div className="space-y-1">
                <Label className="text-xs">Email Address</Label>
                <Input
                  type="email"
                  value={notifyEmail}
                  onChange={(e) => setNotifyEmail(e.target.value)}
                  placeholder="you@example.com"
                  className="h-8 text-sm"
                />
              </div>
              <p className="text-[10px] text-muted-foreground">
                Requires PAPERBOT_NOTIFY_SMTP_* env vars on the backend. The email address here overrides PAPERBOT_NOTIFY_EMAIL_TO.
              </p>
            </div>
          )}
        </section>

        <section className="space-y-2">
          <label className="flex items-center gap-2 text-sm font-medium">
            <Checkbox checked={resendEnabled} onCheckedChange={(v) => setResendEnabled(Boolean(v))} />
            <MailIcon className="size-4" /> Newsletter (Resend)
          </label>
          {resendEnabled && (
            <div className="ml-6 space-y-2">
              <p className="text-[10px] text-muted-foreground">
                Send digest to all newsletter subscribers via Resend API. Requires PAPERBOT_RESEND_API_KEY env var.
              </p>
              <NewsletterSubscribeWidget />
            </div>
          )}
        </section>
    </div>
  )
}

/* ── Newsletter Subscribe Widget ─────────────────────── */

function NewsletterSubscribeWidget() {
  const [email, setEmail] = useState("")
  const [status, setStatus] = useState<"idle" | "loading" | "ok" | "error">("idle")
  const [message, setMessage] = useState("")
  const [subCount, setSubCount] = useState<{ active: number; total: number } | null>(null)

  const fetchCount = useCallback(async () => {
    try {
      const res = await fetch("/api/newsletter/subscribers")
      if (res.ok) setSubCount(await res.json())
    } catch { /* ignore */ }
  }, [])

  useEffect(() => { fetchCount() }, [fetchCount])

  async function handleSubscribe() {
    if (!email.trim()) return
    setStatus("loading"); setMessage("")
    try {
      const res = await fetch("/api/newsletter/subscribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim() }),
      })
      const data = await res.json()
      if (res.ok) {
        setStatus("ok"); setMessage(data.message || "Subscribed!"); setEmail("")
        fetchCount()
      } else {
        setStatus("error"); setMessage(data.detail || "Failed to subscribe")
      }
    } catch (err) {
      setStatus("error"); setMessage(String(err))
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-1.5">
        <Input
          type="email"
          value={email}
          onChange={(e) => { setEmail(e.target.value); setStatus("idle") }}
          placeholder="subscriber@example.com"
          className="h-8 text-sm"
          onKeyDown={(e) => e.key === "Enter" && handleSubscribe()}
        />
        <Button size="sm" className="h-8 text-xs" onClick={handleSubscribe} disabled={status === "loading"}>
          {status === "loading" ? <Loader2Icon className="size-3 animate-spin" /> : "Subscribe"}
        </Button>
      </div>
      {message && (
        <p className={`text-[10px] ${status === "ok" ? "text-green-600" : "text-destructive"}`}>{message}</p>
      )}
      {subCount && (
        <p className="text-[10px] text-muted-foreground">{subCount.active} active subscriber{subCount.active !== 1 ? "s" : ""}</p>
      )}
    </div>
  )
}

/* ── Main Dashboard ───────────────────────────────────── */

export default function TopicWorkflowDashboard() {
  /* Config state (local — queries only) */
  const [queryItems, setQueryItems] = useState<string[]>([...DEFAULT_QUERIES])

  /* Persisted state (zustand) */
  const store = useWorkflowStore()
  const { searchResult, dailyResult, phase, analyzeLog, notifyEmail, notifyEnabled, config } = store
  const resendEnabled = store.resendEnabled
  const uc = store.updateConfig

  /* Derived config accessors — read from persisted store */
  const topK = config.topK
  const setTopK = (v: number) => uc({ topK: v })
  const topN = config.topN
  const setTopN = (v: number) => uc({ topN: v })
  const showPerBranch = config.showPerBranch
  const setShowPerBranch = (v: number) => uc({ showPerBranch: v })
  const saveDaily = config.saveDaily
  const setSaveDaily = (v: boolean) => uc({ saveDaily: v })
  const outputDir = config.outputDir
  const setOutputDir = (v: string) => uc({ outputDir: v })
  const useArxiv = config.useArxiv
  const setUseArxiv = (v: boolean) => uc({ useArxiv: v })
  const useVenue = config.useVenue
  const setUseVenue = (v: boolean) => uc({ useVenue: v })
  const usePapersCool = config.usePapersCool
  const setUsePapersCool = (v: boolean) => uc({ usePapersCool: v })
  const useArxivApi = config.useArxivApi
  const setUseArxivApi = (v: boolean) => uc({ useArxivApi: v })
  const useHFDaily = config.useHFDaily
  const setUseHFDaily = (v: boolean) => uc({ useHFDaily: v })
  const enableLLM = config.enableLLM
  const setEnableLLM = (v: boolean) => uc({ enableLLM: v })
  const useSummary = config.useSummary
  const setUseSummary = (v: boolean) => uc({ useSummary: v })
  const useTrends = config.useTrends
  const setUseTrends = (v: boolean) => uc({ useTrends: v })
  const useInsight = config.useInsight
  const setUseInsight = (v: boolean) => uc({ useInsight: v })
  const useRelevance = config.useRelevance
  const setUseRelevance = (v: boolean) => uc({ useRelevance: v })
  const enableJudge = config.enableJudge
  const setEnableJudge = (v: boolean) => uc({ enableJudge: v })
  const judgeRuns = config.judgeRuns
  const setJudgeRuns = (v: number) => uc({ judgeRuns: v })
  const judgeMaxItems = config.judgeMaxItems
  const setJudgeMaxItems = (v: number) => uc({ judgeMaxItems: v })
  const judgeTokenBudget = config.judgeTokenBudget
  const setJudgeTokenBudget = (v: number) => uc({ judgeTokenBudget: v })

  /* Transient loading state (not persisted) */
  const [loadingSearch, setLoadingSearch] = useState(false)
  const [loadingDaily, setLoadingDaily] = useState(false)
  const [loadingAnalyze, setLoadingAnalyze] = useState(false)
  const [analyzeProgress, setAnalyzeProgress] = useState({ done: 0, total: 0 })
  const [loadingRepos, setLoadingRepos] = useState(false)
  const [repoRows, setRepoRows] = useState<RepoRow[]>([])
  const [repoError, setRepoError] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  /* Stream progress state */
  const [streamPhase, setStreamPhase] = useState<StreamPhase>("idle")
  const [streamLog, setStreamLog] = useState<string[]>([])
  const [streamProgress, setStreamProgress] = useState({ done: 0, total: 0 })
  const streamStartRef = useRef<number | null>(null)

  const addStreamLog = useCallback((line: string) => {
    setStreamLog((prev) => [...prev.slice(-50), line])
  }, [])

  /* UI state */
  const [dagOpen, setDagOpen] = useState(false)
  const [selectedPaper, setSelectedPaper] = useState<SearchItem | null>(null)
  const [sortBy, setSortBy] = useState<"score" | "judge">("score")

  const queries = useMemo(() => queryItems.map((q) => q.trim()).filter(Boolean), [queryItems])
  const branches = useMemo(() => [useArxiv ? "arxiv" : "", useVenue ? "venue" : ""].filter(Boolean), [useArxiv, useVenue])
  const sources = useMemo(
    () => [
      usePapersCool ? "papers_cool" : "",
      useArxivApi ? "arxiv_api" : "",
      useHFDaily ? "hf_daily" : "",
    ].filter(Boolean),
    [usePapersCool, useArxivApi, useHFDaily],
  )
  const llmFeatures = useMemo(
    () => [useSummary ? "summary" : "", useTrends ? "trends" : "", useInsight ? "insight" : "", useRelevance ? "relevance" : ""].filter(Boolean),
    [useInsight, useRelevance, useSummary, useTrends],
  )

  const hasSearchData = Boolean((searchResult?.items?.length || 0) > 0 || dailyResult?.report)
  const hasReportData = Boolean(dailyResult?.report)
  const hasLLMData = Boolean(
    (dailyResult?.report?.llm_analysis?.daily_insight || "").trim() ||
      (dailyResult?.report?.llm_analysis?.query_trends?.length || 0) > 0,
  )
  const hasJudgeData = Boolean(
    dailyResult?.report?.judge?.enabled ||
      (dailyResult?.report?.queries || []).some((query) =>
        (query.top_items || []).some((item) => (item.judge?.overall || 0) > 0),
      ),
  )
  const schedulerDone = Boolean(dailyResult?.markdown_path)

  const dagStatuses = useMemo(
    () =>
      buildDagStatuses({
        phase,
        hasError: Boolean(error),
        llmIntent: enableLLM,
        judgeIntent: enableJudge,
        hasSearchData,
        hasReportData,
        hasLLMData,
        hasJudgeData,
        schedulerDone,
      }),
    [phase, error, enableLLM, enableJudge, hasSearchData, hasReportData, hasLLMData, hasJudgeData, schedulerDone],
  )

  const paperDataSource = dailyResult?.report?.queries ? "dailypaper" : searchResult?.items ? "search" : null

  const allPapers = useMemo(() => {
    const items: Array<SearchItem & { _query?: string }> = []
    if (dailyResult?.report?.queries) {
      for (const q of dailyResult.report.queries) {
        for (const item of q.top_items || []) {
          items.push({ ...item, _query: q.normalized_query || q.raw_query })
        }
      }
    } else if (searchResult?.items) {
      for (const item of searchResult.items) { items.push(item) }
    }
    const seen = new Set<string>()
    const deduped = items.filter((i) => { if (seen.has(i.title)) return false; seen.add(i.title); return true })
    if (sortBy === "judge") { deduped.sort((a, b) => (b.judge?.overall ?? 0) - (a.judge?.overall ?? 0)) }
    else { deduped.sort((a, b) => (b.score ?? 0) - (a.score ?? 0)) }
    return deduped
  }, [dailyResult, searchResult, sortBy])

  const judgedPapersCount = allPapers.filter((p) => (p.judge?.overall ?? 0) > 0).length
  const hasInsightData = Boolean((dailyResult?.report?.llm_analysis?.daily_insight || "").trim())
  const hasTrendData = (dailyResult?.report?.llm_analysis?.query_trends || []).length > 0
  const hasLLMContent = hasInsightData || hasTrendData
  const hasJudgeContent = hasJudgeData || judgedPapersCount > 0

  const queryHighlightRows = useMemo(() => {
    const rows: Array<{
      query: string
      title: string
      score: number
      recommendation: string
      url: string
    }> = []
    const queriesList = dailyResult?.report?.queries || []
    for (const q of queriesList) {
      const queryName = q.normalized_query || q.raw_query || "-"
      for (const item of (q.top_items || []).slice(0, 5)) {
        rows.push({
          query: queryName,
          title: item.title || "Untitled",
          score: Number(item.score || 0),
          recommendation: item.judge?.recommendation || "-",
          url: item.url || "",
        })
      }
    }
    return rows
  }, [dailyResult])

  const globalTopRows = useMemo(() => {
    return (dailyResult?.report?.global_top || []).slice(0, 10).map((item, index) => ({
      rank: index + 1,
      title: item.title || "Untitled",
      score: Number(item.score || 0),
      queries: (item.matched_queries || []).join(", ") || "-",
      url: item.url || "",
    }))
  }, [dailyResult])

  /* Actions */
  async function runTopicSearch() {
    setLoadingSearch(true); setError(null); store.setPhase("searching")
    store.setDailyResult(null); store.clearAnalyzeLog()
    try {
      const res = await fetch("/api/research/paperscool/search", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ queries, sources, branches, top_k_per_query: topK, show_per_branch: showPerBranch }),
      })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      store.setSearchResult(data)
      store.setPhase("searched")
    } catch (err) { setError(String(err)); store.setPhase("error") } finally { setLoadingSearch(false) }
  }

  async function runDailyPaperStream() {
    setLoadingDaily(true); setError(null); setRepoRows([]); setRepoError(null)
    store.setPhase("reporting"); store.clearAnalyzeLog()
    setStreamPhase("search"); setStreamLog([]); setStreamProgress({ done: 0, total: 0 })
    streamStartRef.current = Date.now()

    const requestBody = {
      queries, sources, branches, top_k_per_query: topK, show_per_branch: showPerBranch, top_n: topN,
      title: "DailyPaper Digest", formats: ["both"], save: saveDaily, output_dir: outputDir,
      enable_llm_analysis: enableLLM, llm_features: llmFeatures,
      enable_judge: enableJudge, judge_runs: judgeRuns,
      judge_max_items_per_query: judgeMaxItems, judge_token_budget: judgeTokenBudget,
      notify: notifyEnabled || resendEnabled,
      notify_channels: [...(notifyEnabled ? ["email"] : []), ...(resendEnabled ? ["resend"] : [])],
      notify_email_to: notifyEnabled && notifyEmail.trim() ? [notifyEmail.trim()] : [],
    }

    let streamFailed = false
    try {
      const res = await fetch("/api/research/paperscool/daily", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "text/event-stream, application/json" },
        body: JSON.stringify(requestBody),
      })
      if (!res.ok) throw new Error(await res.text())

      const contentType = res.headers.get("content-type") || ""

      // JSON fallback (fast path — no LLM/Judge)
      if (!contentType.includes("text/event-stream")) {
        const data = await res.json()
        store.setDailyResult(data)
        store.setPhase("reported")
        setStreamPhase("done")
        return
      }

      // SSE streaming path
      if (!res.body) throw new Error("No response body for SSE stream")

      for await (const event of readSSE(res.body)) {
        if (event.type === "progress") {
          const d = (event.data || {}) as { phase?: string; message?: string; total?: number }
          const p = (d.phase || "search") as StreamPhase
          setStreamPhase(p)
          addStreamLog(`[${p}] ${d.message || "running"}`)
          if (d.total && d.total > 0) {
            setStreamProgress({ done: 0, total: d.total })
          }
          continue
        }

        if (event.type === "search_done") {
          const d = (event.data || {}) as { items_count?: number; unique_items?: number }
          addStreamLog(`search done: ${d.unique_items || 0} unique papers`)
          setStreamPhase("build")
          continue
        }

        if (event.type === "report_built") {
          const d = (event.data || {}) as { report?: DailyResult["report"]; queries_count?: number; global_top_count?: number }
          addStreamLog(`report built: ${d.queries_count || 0} queries, ${d.global_top_count || 0} global top`)
          if (d.report) {
            store.setDailyResult({ report: d.report, markdown: "" })
          }
          continue
        }

        if (event.type === "llm_summary") {
          const d = (event.data || {}) as { title?: string; query?: string; ai_summary?: string; done?: number; total?: number }
          setStreamProgress({ done: d.done || 0, total: d.total || 0 })
          addStreamLog(`summary ${d.done || 0}/${d.total || 0}: ${d.title || "paper"}`)
          if (d.query && d.title && d.ai_summary) {
            store.updateDailyResult((prev) => {
              const nextQueries = (prev.report.queries || []).map((query) => {
                const queryName = query.normalized_query || query.raw_query || ""
                if (queryName !== d.query) return query
                const nextItems = (query.top_items || []).map((item) => {
                  if (item.title === d.title) return { ...item, ai_summary: d.ai_summary }
                  return item
                })
                return { ...query, top_items: nextItems }
              })
              return { ...prev, report: { ...prev.report, queries: nextQueries } }
            })
          }
          continue
        }

        if (event.type === "trend") {
          const d = (event.data || {}) as { query?: string; analysis?: string; done?: number; total?: number }
          addStreamLog(`trend ${d.done || 0}/${d.total || 0}: ${d.query || "query"}`)
          if (d.query && typeof d.analysis === "string") {
            store.updateDailyResult((prev) => {
              const llmAnalysis = prev.report.llm_analysis || { enabled: true, features: [], daily_insight: "", query_trends: [] }
              const features = new Set(llmAnalysis.features || [])
              features.add("trends")
              const trendList = [...(llmAnalysis.query_trends || [])]
              const existingIndex = trendList.findIndex((item) => item.query === d.query)
              if (existingIndex >= 0) {
                trendList[existingIndex] = { query: d.query!, analysis: d.analysis! }
              } else {
                trendList.push({ query: d.query!, analysis: d.analysis! })
              }
              return {
                ...prev,
                report: {
                  ...prev.report,
                  llm_analysis: { ...llmAnalysis, enabled: true, features: Array.from(features), query_trends: trendList },
                },
              }
            })
          }
          continue
        }

        if (event.type === "insight") {
          const d = (event.data || {}) as { analysis?: string }
          addStreamLog("insight generated")
          if (typeof d.analysis === "string") {
            store.updateDailyResult((prev) => {
              const llmAnalysis = prev.report.llm_analysis || { enabled: true, features: [], daily_insight: "", query_trends: [] }
              const features = new Set(llmAnalysis.features || [])
              features.add("insight")
              return {
                ...prev,
                report: {
                  ...prev.report,
                  llm_analysis: { ...llmAnalysis, enabled: true, features: Array.from(features), daily_insight: d.analysis! },
                },
              }
            })
          }
          continue
        }

        if (event.type === "llm_done") {
          const d = (event.data || {}) as { summaries_count?: number; trends_count?: number }
          addStreamLog(`LLM done: ${d.summaries_count || 0} summaries, ${d.trends_count || 0} trends`)
          setStreamPhase("judge")
          continue
        }

        if (event.type === "judge") {
          const d = (event.data || {}) as { query?: string; title?: string; judge?: SearchItem["judge"]; done?: number; total?: number }
          setStreamProgress({ done: d.done || 0, total: d.total || 0 })
          setStreamPhase("judge")
          const rec = d.judge?.recommendation || "?"
          const overall = d.judge?.overall != null ? Number(d.judge.overall).toFixed(2) : "?"
          addStreamLog(`judge ${d.done || 0}/${d.total || 0}: [${rec} ${overall}] ${d.title || "paper"} (${d.query || ""})`)
          if (d.query && d.title && d.judge) {
            store.updateDailyResult((prev) => {
              const sourceQueries = prev.report.queries || []
              let matched = false
              const nextQueries = sourceQueries.map((query) => {
                const queryName = query.normalized_query || query.raw_query || ""
                if (queryName !== d.query) return query
                const nextItems = (query.top_items || []).map((item) => {
                  if (item.title === d.title) { matched = true; return { ...item, judge: d.judge } }
                  return item
                })
                return { ...query, top_items: nextItems }
              })
              if (!matched) {
                const fallbackQueries = nextQueries.map((query) => {
                  if (matched) return query
                  const nextItems = (query.top_items || []).map((item) => {
                    if (!matched && item.title === d.title) { matched = true; return { ...item, judge: d.judge } }
                    return item
                  })
                  return { ...query, top_items: nextItems }
                })
                return { ...prev, report: { ...prev.report, queries: fallbackQueries } }
              }
              return { ...prev, report: { ...prev.report, queries: nextQueries } }
            })
          }
          continue
        }

        if (event.type === "judge_done") {
          const d = (event.data || {}) as DailyResult["report"]["judge"]
          store.updateDailyResult((prev) => ({
            ...prev,
            report: { ...prev.report, judge: d || prev.report.judge },
          }))
          addStreamLog("judge scoring complete")
          continue
        }

        if (event.type === "filter_done") {
          const d = (event.data || {}) as {
            total_before?: number
            total_after?: number
            removed_count?: number
            log?: Array<{ query?: string; title?: string; recommendation?: string; overall?: number; action?: string }>
          }
          setStreamPhase("filter")
          addStreamLog(`filter: ${d.total_before || 0} papers -> ${d.total_after || 0} kept, ${d.removed_count || 0} removed`)
          if (d.log) {
            for (const entry of d.log) {
              addStreamLog(`  removed [${entry.recommendation || "?"}] ${entry.title || "?"} (${entry.query || ""})`)
            }
          }
          // Update the store with filtered report — the next "result" event will have the final state
          // but we can also re-fetch queries from the filter event if needed
          continue
        }

        if (event.type === "result") {
          const d = (event.data || {}) as {
            report?: DailyResult["report"]
            markdown?: string
            markdown_path?: string | null
            json_path?: string | null
            notify_result?: Record<string, unknown> | null
          }
          if (d.report) {
            store.setDailyResult({
              report: d.report,
              markdown: typeof d.markdown === "string" ? d.markdown : "",
              markdown_path: d.markdown_path,
              json_path: d.json_path,
            })
          }
          setStreamPhase("done")
          addStreamLog("stream complete")
          continue
        }

        if (event.type === "error") {
          const d = (event.data || {}) as { message?: string; detail?: string }
          const msg = event.message || d.message || d.detail || "Unknown stream error"
          addStreamLog(`[error] ${msg}`)
          setError(`DailyPaper failed: ${msg}`)
          streamFailed = true
          setStreamPhase("error")
          store.setPhase("error")
          break
        }
      }
      if (!streamFailed) {
        store.setPhase("reported")
      }
    } catch (err) {
      streamFailed = true
      setError(String(err))
      setStreamPhase("error")
      store.setPhase("error")
    } finally {
      setLoadingDaily(false)
      streamStartRef.current = null
    }
  }

  async function runAnalyzeStream() {
    if (!dailyResult?.report) { setError("Generate DailyPaper first."); return }
    const runJudge = Boolean(enableJudge)
    const runTrends = Boolean(enableLLM && useTrends)
    const runInsight = Boolean(enableLLM && useInsight)
    if (!runJudge && !runTrends && !runInsight) { setError("Enable Judge, LLM trends, or LLM insight before analyzing."); return }

    setLoadingAnalyze(true); setError(null); store.clearAnalyzeLog(); setAnalyzeProgress({ done: 0, total: 0 }); store.setPhase("reporting")
    setStreamPhase("idle"); setStreamLog([]); setStreamProgress({ done: 0, total: 0 })
    streamStartRef.current = Date.now()
    store.addAnalyzeLog(
      `[start] run_judge=${runJudge} run_trends=${runTrends} run_insight=${runInsight} llm_enabled=${enableLLM} judge_enabled=${enableJudge}`,
    )
    if (enableLLM && !useTrends && !useInsight) {
      store.addAnalyzeLog("[hint] Analyze stream currently supports trends and daily insight.")
    }

    let streamFailed = false
    try {
      const res = await fetch("/api/research/paperscool/analyze", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          report: dailyResult.report, run_judge: runJudge, run_trends: runTrends, run_insight: runInsight,
          judge_runs: judgeRuns, judge_max_items_per_query: judgeMaxItems,
          judge_token_budget: judgeTokenBudget, trend_max_items_per_query: 3,
        }),
      })
      if (!res.ok || !res.body) throw new Error(await res.text())

      for await (const event of readSSE(res.body)) {
        if (event.type === "progress") {
          const d = (event.data || {}) as { phase?: string; message?: string; total?: number }
          store.addAnalyzeLog(`[${d.phase || "step"}] ${d.message || "running"}`)
          if (d.phase === "judge" && (d.total || 0) > 0) {
            setAnalyzeProgress({ done: 0, total: d.total || 0 })
          }
          continue
        }

        if (event.type === "trend") {
          const d = (event.data || {}) as {
            query?: string
            analysis?: string
            done?: number
            total?: number
          }
          store.addAnalyzeLog(`trend ${d.done || 0}/${d.total || 0}: ${d.query || "query"}`)
          const trendQuery = d.query
          const trendAnalysis = d.analysis
          if (trendQuery && typeof trendAnalysis === "string") {
            store.updateDailyResult((prev) => {
              const llmAnalysis = prev.report.llm_analysis || {
                enabled: true,
                features: [],
                daily_insight: "",
                query_trends: [],
              }
              const features = new Set(llmAnalysis.features || [])
              features.add("trends")
              const trendList = [...(llmAnalysis.query_trends || [])]
              const existingIndex = trendList.findIndex((item) => item.query === trendQuery)
              if (existingIndex >= 0) {
                trendList[existingIndex] = { query: trendQuery, analysis: trendAnalysis }
              } else {
                trendList.push({ query: trendQuery, analysis: trendAnalysis })
              }
              return {
                ...prev,
                report: {
                  ...prev.report,
                  llm_analysis: {
                    ...llmAnalysis,
                    enabled: true,
                    features: Array.from(features),
                    query_trends: trendList,
                  },
                },
              }
            })
          }
          continue
        }

        if (event.type === "insight") {
          const d = (event.data || {}) as {
            analysis?: string
          }
          const insight = d.analysis
          store.addAnalyzeLog("insight generated")
          if (typeof insight === "string") {
            store.updateDailyResult((prev) => {
              const llmAnalysis = prev.report.llm_analysis || {
                enabled: true,
                features: [],
                daily_insight: "",
                query_trends: [],
              }
              const features = new Set(llmAnalysis.features || [])
              features.add("insight")
              return {
                ...prev,
                report: {
                  ...prev.report,
                  llm_analysis: {
                    ...llmAnalysis,
                    enabled: true,
                    features: Array.from(features),
                    daily_insight: insight,
                  },
                },
              }
            })
          }
          continue
        }

        if (event.type === "judge") {
          const d = (event.data || {}) as {
            query?: string
            title?: string
            judge?: SearchItem["judge"]
            done?: number
            total?: number
          }
          setAnalyzeProgress({ done: d.done || 0, total: d.total || 0 })
          store.addAnalyzeLog(`judge ${d.done || 0}/${d.total || 0}: ${d.title || "paper"}`)

          if (d.query && d.title && d.judge) {
            store.updateDailyResult((prev) => {
              const sourceQueries = prev.report.queries || []
              let matched = false
              const nextQueries = sourceQueries.map((query) => {
                const queryName = query.normalized_query || query.raw_query || ""
                if (queryName !== d.query) {
                  return query
                }
                const nextItems = (query.top_items || []).map((item) => {
                  if (item.title === d.title) {
                    matched = true
                    return { ...item, judge: d.judge }
                  }
                  return item
                })
                return { ...query, top_items: nextItems }
              })

              if (!matched) {
                const fallbackQueries = nextQueries.map((query) => {
                  if (matched) {
                    return query
                  }
                  const nextItems = (query.top_items || []).map((item) => {
                    if (!matched && item.title === d.title) {
                      matched = true
                      return { ...item, judge: d.judge }
                    }
                    return item
                  })
                  return { ...query, top_items: nextItems }
                })
                return {
                  ...prev,
                  report: {
                    ...prev.report,
                    queries: fallbackQueries,
                  },
                }
              }

              return {
                ...prev,
                report: {
                  ...prev.report,
                  queries: nextQueries,
                },
              }
            })
          }
          continue
        }

        if (event.type === "judge_done") {
          const d = (event.data || {}) as DailyResult["report"]["judge"]
          store.updateDailyResult((prev) => ({
            ...prev,
            report: {
              ...prev.report,
              judge: d || prev.report.judge,
            },
          }))
          continue
        }

        if (event.type === "result") {
          const d = (event.data || {}) as { report?: DailyResult["report"]; markdown?: string }
          if (d.report) {
            store.updateDailyResult((prev) => ({
              ...prev,
              report: d.report || prev.report,
              markdown: typeof d.markdown === "string" ? d.markdown : prev.markdown,
            }))
          }
          continue
        }

        if (event.type === "error") {
          const d = (event.data || {}) as { message?: string; detail?: string }
          const msg = event.message || d.message || d.detail || "Unknown analyze stream error"
          store.addAnalyzeLog(`[error] ${msg}`)
          setError(`Analyze failed: ${msg}`)
          streamFailed = true
          store.setPhase("error")
          break
        }
      }
      if (!streamFailed) {
        store.setPhase("reported")
      }
    } catch (err) {
      streamFailed = true
      setError(String(err))
      store.setPhase("error")
    } finally {
      setLoadingAnalyze(false)
      streamStartRef.current = null
    }
  }

  async function runRepoEnrichment() {
    if (!dailyResult?.report) {
      setRepoError("Generate DailyPaper first.")
      return
    }

    setLoadingRepos(true)
    setRepoError(null)
    try {
      const res = await fetch("/api/research/paperscool/repos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          report: dailyResult.report,
          max_items: 500,
          include_github_api: true,
        }),
      })
      if (!res.ok) throw new Error(await res.text())
      const payload = await res.json() as { repos?: RepoRow[] }
      setRepoRows(payload.repos || [])
    } catch (err) {
      setRepoError(String(err))
    } finally {
      setLoadingRepos(false)
    }
  }

  const isLoading = loadingSearch || loadingDaily || loadingAnalyze
  const canSearch = queries.length > 0 && branches.length > 0 && sources.length > 0
  const loadingLabel = loadingSearch
    ? "Searching sources..."
    : "Running judge/trend/insight enrichment..."
  const loadingHint = loadingAnalyze && analyzeProgress.total > 0
    ? `${analyzeProgress.done}/${analyzeProgress.total} judged`
    : loadingSearch
      ? "Multi-query retrieval in progress"
      : "Waiting for LLM events"

  return (
    <div className="space-y-4">
      <PaperDetailDialog item={selectedPaper} open={Boolean(selectedPaper)} onClose={() => setSelectedPaper(null)} />

      {/* Header */}
      <div className="flex items-center justify-between gap-4">
        <div className="min-w-0">
          <h2 className="text-xl font-bold">Topic Workflow</h2>
          <p className="text-sm text-muted-foreground">
            Search, analyze, and judge research papers
            {store.lastUpdated && <span className="ml-2 text-[10px]">(last: {new Date(store.lastUpdated).toLocaleString()})</span>}
          </p>
        </div>
        <div className="flex flex-shrink-0 items-center gap-2">
          <Button size="sm" disabled={isLoading || !canSearch} onClick={runTopicSearch}>
            {loadingSearch ? <Loader2Icon className="mr-1.5 size-4 animate-spin" /> : <PlayIcon className="mr-1.5 size-4" />} Search
          </Button>
          <Button size="sm" variant="secondary" disabled={isLoading || !canSearch} onClick={runDailyPaperStream}>
            {loadingDaily ? <Loader2Icon className="mr-1.5 size-4 animate-spin" /> : <BookOpenIcon className="mr-1.5 size-4" />} DailyPaper
          </Button>
          <Button size="sm" variant="outline" disabled={isLoading || !dailyResult?.report} onClick={runAnalyzeStream}>
            {loadingAnalyze ? <Loader2Icon className="mr-1.5 size-4 animate-spin" /> : <ZapIcon className="mr-1.5 size-4" />} Analyze
          </Button>
          <Separator orientation="vertical" className="mx-1 h-6" />
          <Button size="sm" variant="ghost" title="Clear cached data" onClick={() => { store.clearAll(); setError(null) }}>
            <Trash2Icon className="size-4" />
          </Button>
          <Sheet>
            <SheetTrigger asChild>
              <Button size="sm" variant="ghost"><SettingsIcon className="size-4" /></Button>
            </SheetTrigger>
            <SheetContent side="right" className="w-[400px] sm:max-w-[400px] overflow-hidden">
              <SheetHeader>
                <SheetTitle>Workflow Configuration</SheetTitle>
                <SheetDescription>Topics, sources, LLM and Judge settings</SheetDescription>
              </SheetHeader>
              <div className="flex-1 overflow-y-auto px-1 pb-6">
                <ConfigSheetBody {...{
                queryItems, setQueryItems, topK, setTopK, topN, setTopN,
                showPerBranch, setShowPerBranch, saveDaily, setSaveDaily,
                outputDir, setOutputDir, useArxiv, setUseArxiv, useVenue, setUseVenue,
                usePapersCool, setUsePapersCool, useArxivApi, setUseArxivApi, useHFDaily, setUseHFDaily, enableLLM, setEnableLLM,
                useSummary, setUseSummary, useTrends, setUseTrends,
                useInsight, setUseInsight, useRelevance, setUseRelevance,
                enableJudge, setEnableJudge, judgeRuns, setJudgeRuns,
                judgeMaxItems, setJudgeMaxItems, judgeTokenBudget, setJudgeTokenBudget,
                notifyEmail, setNotifyEmail: store.setNotifyEmail,
                notifyEnabled, setNotifyEnabled: store.setNotifyEnabled,
                resendEnabled, setResendEnabled: store.setResendEnabled,
              }} />
              </div>
            </SheetContent>
          </Sheet>
        </div>
      </div>

      {error && <div className="rounded-lg border border-red-300 bg-red-50 px-4 py-2 text-sm text-red-700">{error}</div>}

      {/* Stream progress card for DailyPaper SSE */}
      {loadingDaily && streamPhase !== "idle" && (
        <StreamProgressCard
          streamPhase={streamPhase}
          streamLog={streamLog}
          streamProgress={streamProgress}
          startTime={streamStartRef.current}
        />
      )}

      {/* Generic loading card for search / analyze */}
      {isLoading && !loadingDaily && !loadingAnalyze && (
        <Card className="border-blue-200 bg-blue-50/40">
          <CardContent className="space-y-2 py-3">
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2 font-medium text-blue-900">
                <Loader2Icon className="size-4 animate-spin" />
                {loadingLabel}
              </div>
              <span className="text-xs text-blue-700">{loadingHint}</span>
            </div>
            <Progress value={loadingAnalyze && analyzeProgress.total > 0 ? (analyzeProgress.done / analyzeProgress.total) * 100 : 35} />
            <p className="text-xs text-blue-800/80">任务执行中，结果会逐步填充，不会空白等待。</p>
          </CardContent>
        </Card>
      )}

      {(loadingAnalyze || analyzeLog.length > 0) && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Analyze Progress</CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-24">
              <div className="space-y-0.5 font-mono text-xs text-muted-foreground">
                {analyzeLog.slice(-12).map((line, idx) => (<div key={`global-log-${idx}`}>{line}</div>))}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      )}

      {/* Stats Row */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatCard label="Queries" value={queries.length} icon={<FilterIcon className="size-5" />} />
        <StatCard label="Papers Found" value={searchResult?.summary?.unique_items ?? dailyResult?.report?.stats?.unique_items ?? 0} icon={<BookOpenIcon className="size-5" />} />
        <StatCard label="Judged" value={judgedPapersCount} icon={<StarIcon className="size-5" />} />
        <StatCard label="Phase" value={phase} icon={<TrendingUpIcon className="size-5" />} />
      </div>

      {/* DAG (collapsible) */}
      <Card>
        <CardHeader className="cursor-pointer py-3" onClick={() => setDagOpen(!dagOpen)}>
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm">Workflow DAG</CardTitle>
            <div className="flex items-center gap-2">
              <div className="flex gap-1">
                {Object.entries(dagStatuses).map(([key, status]) => (
                  <div key={key} className={`size-2 rounded-full ${status === "done" ? "bg-green-500" : status === "running" ? "bg-blue-500 animate-pulse" : status === "error" ? "bg-red-500" : status === "skipped" ? "bg-slate-300" : "bg-slate-200"}`} title={`${key}: ${status}`} />
                ))}
              </div>
              {dagOpen ? <ChevronDownIcon className="size-4" /> : <ChevronRightIcon className="size-4" />}
            </div>
          </div>
        </CardHeader>
        {dagOpen && (
          <CardContent className="pt-0">
            <WorkflowDagView statuses={dagStatuses} queriesCount={queries.length} hitCount={searchResult?.summary?.total_query_hits ?? dailyResult?.report?.stats?.total_query_hits ?? 0} uniqueCount={searchResult?.summary?.unique_items ?? dailyResult?.report?.stats?.unique_items ?? 0} llmEnabled={enableLLM || hasLLMData} judgeEnabled={enableJudge || hasJudgeData} />
          </CardContent>
        )}
      </Card>

      {/* Result Tabs */}
      <Tabs defaultValue="papers" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="papers" className="gap-1.5"><BookOpenIcon className="size-3.5" /> Papers</TabsTrigger>
          <TabsTrigger value="insights" className="gap-1.5"><SparklesIcon className="size-3.5" /> Insights</TabsTrigger>
          <TabsTrigger value="judge" className="gap-1.5"><StarIcon className="size-3.5" /> Judge</TabsTrigger>
          <TabsTrigger value="markdown" className="gap-1.5"><BookOpenIcon className="size-3.5" /> Report</TabsTrigger>
        </TabsList>

        {/* Papers */}
        <TabsContent value="papers" className="mt-4 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <p className="text-sm text-muted-foreground">{allPapers.length} papers</p>
              {paperDataSource && (
                <Badge variant="outline" className="text-[10px]">
                  {paperDataSource === "dailypaper" ? "DailyPaper" : "Search"}
                </Badge>
              )}
            </div>
            <div className="flex items-center gap-2">
              <Label className="text-xs">Sort:</Label>
              <select className="h-7 rounded-md border bg-background px-2 text-xs" value={sortBy} onChange={(e) => setSortBy(e.target.value as "score" | "judge")}>
                <option value="score">Search Score</option>
                <option value="judge">Judge Score</option>
              </select>
            </div>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            {allPapers.length > 0 ? (
              allPapers.map((item, idx) => (
                <PaperCard key={`${item.title}-${idx}`} item={item} query={(item as SearchItem & { _query?: string })._query} onOpenDetail={(p) => setSelectedPaper(p)} />
              ))
            ) : isLoading ? (
              Array.from({ length: 4 }).map((_, idx) => (
                <div key={`paper-skeleton-${idx}`} className="rounded-lg border p-4">
                  <div className="h-4 w-4/5 animate-pulse rounded bg-muted" />
                  <div className="mt-2 h-3 w-2/5 animate-pulse rounded bg-muted" />
                  <div className="mt-4 space-y-2">
                    <div className="h-2 w-full animate-pulse rounded bg-muted" />
                    <div className="h-2 w-11/12 animate-pulse rounded bg-muted" />
                    <div className="h-2 w-10/12 animate-pulse rounded bg-muted" />
                  </div>
                </div>
              ))
            ) : (
              <div className="col-span-2 rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
                Run Search to find papers, then DailyPaper to rank and compose a report, then Analyze to run Judge/Trends.
              </div>
            )}
          </div>
        </TabsContent>

        {/* Insights */}
        <TabsContent value="insights" className="mt-4 space-y-4">
          {hasInsightData ? (
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm">Daily Insight</CardTitle></CardHeader>
              <CardContent>
                <div className="prose prose-sm max-w-none dark:prose-invert text-sm">
                  <Markdown remarkPlugins={[remarkGfm]}>{dailyResult?.report?.llm_analysis?.daily_insight || ""}</Markdown>
                </div>
              </CardContent>
            </Card>
          ) : loadingAnalyze ? (
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm">Daily Insight (Generating...)</CardTitle></CardHeader>
              <CardContent className="space-y-2">
                <div className="h-3 w-full animate-pulse rounded bg-muted" />
                <div className="h-3 w-11/12 animate-pulse rounded bg-muted" />
                <div className="h-3 w-9/12 animate-pulse rounded bg-muted" />
              </CardContent>
            </Card>
          ) : null}

          {hasTrendData ? (
            <div className="space-y-3">
              <h3 className="text-sm font-semibold">Query Trend Analysis</h3>
              {(dailyResult?.report?.llm_analysis?.query_trends || []).map((trend, idx) => (
                <Card key={`${trend.query}-${idx}`}>
                  <CardHeader className="pb-2"><CardTitle className="text-sm">{trend.query}</CardTitle></CardHeader>
                  <CardContent>
                    {(trend.analysis || "").trim() ? (
                      <div className="prose prose-sm max-w-none dark:prose-invert text-sm">
                        <Markdown remarkPlugins={[remarkGfm]}>{trend.analysis}</Markdown>
                      </div>
                    ) : (
                      <p className="text-sm text-muted-foreground">No trend content returned by model for this query.</p>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : loadingAnalyze ? (
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm">Query Trend Analysis (Generating...)</CardTitle></CardHeader>
              <CardContent className="space-y-2">
                <div className="h-3 w-1/3 animate-pulse rounded bg-muted" />
                <div className="h-3 w-full animate-pulse rounded bg-muted" />
                <div className="h-3 w-10/12 animate-pulse rounded bg-muted" />
              </CardContent>
            </Card>
          ) : null}

          {!hasLLMContent && !loadingAnalyze && (
            <div className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
              {dailyResult?.report?.llm_analysis?.enabled
                ? "LLM enrichment ran but returned empty content. Check reasoning model route/API key and analyze log."
                : "Run DailyPaper with LLM Analysis enabled, or run Analyze."}
            </div>
          )}
        </TabsContent>

        {/* Judge */}
        <TabsContent value="judge" className="mt-4 space-y-4">
          {dailyResult?.report?.judge?.enabled && (
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              {Object.entries(dailyResult.report.judge.recommendation_count || {}).map(([name, count]) => (
                <div key={name} className={`rounded-lg border px-3 py-2 text-center ${REC_COLORS[name] || ""}`}>
                  <div className="text-lg font-bold">{count}</div>
                  <div className="text-xs">{REC_LABELS[name] || name}</div>
                </div>
              ))}
            </div>
          )}
          {dailyResult?.report?.judge?.budget && (
            <div className="rounded-lg border bg-muted/30 px-4 py-3 text-sm">
              <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
                <span>Candidates: {dailyResult.report.judge.budget.candidate_items ?? 0}</span>
                <span>Judged: {dailyResult.report.judge.budget.judged_items ?? 0}</span>
                <span>Tokens: {dailyResult.report.judge.budget.estimated_tokens ?? 0}/{(dailyResult.report.judge.budget.token_budget ?? 0) > 0 ? dailyResult.report.judge.budget.token_budget : "unlimited"}</span>
                {(dailyResult.report.judge.budget.skipped_due_budget ?? 0) > 0 && <span className="text-yellow-600">Skipped (budget): {dailyResult.report.judge.budget.skipped_due_budget}</span>}
              </div>
            </div>
          )}
          <div className="grid gap-3 md:grid-cols-2">
            {allPapers.filter((p) => (p.judge?.overall ?? 0) > 0).sort((a, b) => (b.judge?.overall ?? 0) - (a.judge?.overall ?? 0)).map((item, idx) => (
              <PaperCard key={`judge-${item.title}-${idx}`} item={item} query={(item as SearchItem & { _query?: string })._query} onOpenDetail={(p) => setSelectedPaper(p)} />
            ))}
            {!hasJudgeContent && (loadingAnalyze ? (
              Array.from({ length: 2 }).map((_, idx) => (
                <div key={`judge-skeleton-${idx}`} className="rounded-lg border p-4">
                  <div className="h-4 w-3/4 animate-pulse rounded bg-muted" />
                  <div className="mt-2 h-3 w-1/3 animate-pulse rounded bg-muted" />
                  <div className="mt-4 h-36 animate-pulse rounded bg-muted" />
                </div>
              ))
            ) : (
              <div className="col-span-2 rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
                {dailyResult?.report?.judge?.enabled
                  ? "Judge ran but no score was attached. Check candidate count/token budget and analyze log."
                  : "Run DailyPaper with Judge enabled, or run Analyze to see judge results."}
              </div>
            ))}
          </div>
          {analyzeLog.length > 0 && (
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm">Analyze Stream Log</CardTitle></CardHeader>
              <CardContent>
                <ScrollArea className="h-32">
                  <div className="space-y-0.5 font-mono text-xs text-muted-foreground">
                    {analyzeLog.map((line, idx) => (<div key={`log-${idx}`}>{line}</div>))}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Report (Structured) */}
        <TabsContent value="markdown" className="mt-4 space-y-3">
          {dailyResult?.report ? (
            <>
              <Card>
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-sm">DailyPaper Report</CardTitle>
                    <div className="flex gap-2 text-xs text-muted-foreground">
                      {dailyResult.markdown_path && <span>MD: {dailyResult.markdown_path}</span>}
                      {dailyResult.json_path && <span>JSON: {dailyResult.json_path}</span>}
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid gap-2 text-xs md:grid-cols-4">
                    <div className="rounded-md border bg-muted/20 px-3 py-2">Date: {dailyResult.report.date}</div>
                    <div className="rounded-md border bg-muted/20 px-3 py-2">Source: {dailyResult.report.source || "papers.cool"}</div>
                    <div className="rounded-md border bg-muted/20 px-3 py-2">Unique: {dailyResult.report.stats.unique_items}</div>
                    <div className="rounded-md border bg-muted/20 px-3 py-2">Hits: {dailyResult.report.stats.total_query_hits}</div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2"><CardTitle className="text-sm">Query Highlights Table</CardTitle></CardHeader>
                <CardContent>
                  {queryHighlightRows.length > 0 ? (
                    <ScrollArea className="h-72 rounded-md border">
                      <table className="w-full text-left text-xs">
                        <thead className="sticky top-0 bg-muted/70 backdrop-blur">
                          <tr>
                            <th className="border-b px-3 py-2 font-medium">Query</th>
                            <th className="border-b px-3 py-2 font-medium">Title</th>
                            <th className="border-b px-3 py-2 font-medium">Score</th>
                            <th className="border-b px-3 py-2 font-medium">Judge</th>
                          </tr>
                        </thead>
                        <tbody>
                          {queryHighlightRows.map((row, idx) => (
                            <tr key={`${row.query}-${row.title}-${idx}`} className="odd:bg-muted/20">
                              <td className="border-b px-3 py-2 text-muted-foreground">{row.query}</td>
                              <td className="border-b px-3 py-2">
                                {row.url ? <a href={row.url} target="_blank" rel="noreferrer" className="hover:underline text-primary">{row.title}</a> : row.title}
                              </td>
                              <td className="border-b px-3 py-2 font-mono">{row.score.toFixed(4)}</td>
                              <td className="border-b px-3 py-2">
                                <Badge variant="outline" className={REC_COLORS[row.recommendation] || ""}>{REC_LABELS[row.recommendation] || row.recommendation}</Badge>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </ScrollArea>
                  ) : (
                    <div className="rounded-md border border-dashed p-6 text-center text-sm text-muted-foreground">No query highlights yet.</div>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2"><CardTitle className="text-sm">Global Top Table</CardTitle></CardHeader>
                <CardContent>
                  {globalTopRows.length > 0 ? (
                    <ScrollArea className="h-64 rounded-md border">
                      <table className="w-full text-left text-xs">
                        <thead className="sticky top-0 bg-muted/70 backdrop-blur">
                          <tr>
                            <th className="border-b px-3 py-2 font-medium">#</th>
                            <th className="border-b px-3 py-2 font-medium">Title</th>
                            <th className="border-b px-3 py-2 font-medium">Score</th>
                            <th className="border-b px-3 py-2 font-medium">Matched Queries</th>
                          </tr>
                        </thead>
                        <tbody>
                          {globalTopRows.map((row) => (
                            <tr key={`${row.rank}-${row.title}`} className="odd:bg-muted/20">
                              <td className="border-b px-3 py-2 font-mono">{row.rank}</td>
                              <td className="border-b px-3 py-2">
                                {row.url ? <a href={row.url} target="_blank" rel="noreferrer" className="hover:underline text-primary">{row.title}</a> : row.title}
                              </td>
                              <td className="border-b px-3 py-2 font-mono">{row.score.toFixed(4)}</td>
                              <td className="border-b px-3 py-2 text-muted-foreground">{row.queries}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </ScrollArea>
                  ) : (
                    <div className="rounded-md border border-dashed p-6 text-center text-sm text-muted-foreground">No global top papers yet.</div>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between gap-2">
                    <CardTitle className="text-sm">Repository Enrichment</CardTitle>
                    <Button size="sm" variant="outline" disabled={loadingRepos || !dailyResult?.report} onClick={runRepoEnrichment}>
                      {loadingRepos ? <Loader2Icon className="mr-1.5 size-4 animate-spin" /> : null}
                      {loadingRepos ? "Enriching..." : "Find Repos"}
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  {repoError && <div className="mb-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">{repoError}</div>}
                  {repoRows.length > 0 ? (
                    <ScrollArea className="h-64 rounded-md border">
                      <table className="w-full text-left text-xs">
                        <thead className="sticky top-0 bg-muted/70 backdrop-blur">
                          <tr>
                            <th className="border-b px-3 py-2 font-medium">Title</th>
                            <th className="border-b px-3 py-2 font-medium">Repository</th>
                            <th className="border-b px-3 py-2 font-medium">Stars</th>
                            <th className="border-b px-3 py-2 font-medium">Language</th>
                          </tr>
                        </thead>
                        <tbody>
                          {repoRows.map((row, idx) => (
                            <tr key={`${row.repo_url}-${idx}`} className="odd:bg-muted/20">
                              <td className="border-b px-3 py-2">
                                {row.paper_url ? <a href={row.paper_url} target="_blank" rel="noreferrer" className="hover:underline text-primary">{row.title}</a> : row.title}
                              </td>
                              <td className="border-b px-3 py-2">
                                <a href={row.repo_url} target="_blank" rel="noreferrer" className="hover:underline text-primary">{row.repo_url}</a>
                              </td>
                              <td className="border-b px-3 py-2 font-mono">{row.github?.stars ?? "-"}</td>
                              <td className="border-b px-3 py-2 text-muted-foreground">{row.github?.language || "-"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </ScrollArea>
                  ) : (
                    <div className="rounded-md border border-dashed p-6 text-center text-sm text-muted-foreground">Click "Find Repos" to enrich papers with code repositories.</div>
                  )}
                </CardContent>
              </Card>

            </>
          ) : isLoading ? (
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm">Building structured report...</CardTitle></CardHeader>
              <CardContent className="space-y-2">
                <div className="h-8 w-full animate-pulse rounded bg-muted" />
                <div className="h-44 w-full animate-pulse rounded bg-muted" />
              </CardContent>
            </Card>
          ) : (
            <div className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">Generate a DailyPaper to see the rendered report.</div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
