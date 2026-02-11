import { create } from "zustand"
import { persist } from "zustand/middleware"

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

type SearchResult = {
  source: string
  fetched_at: string
  sources: string[]
  items: SearchItem[]
  summary: {
    unique_items: number
    total_query_hits: number
    source_breakdown?: Record<string, number>
  }
}

type LLMAnalysis = {
  enabled?: boolean
  features?: string[]
  daily_insight?: string
  query_trends?: Array<{ query: string; analysis: string }>
}

type JudgeSummary = {
  enabled?: boolean
  max_items_per_query?: number
  n_runs?: number
  recommendation_count?: Record<string, number>
  budget?: {
    token_budget?: number
    estimated_tokens?: number
    candidate_items?: number
    judged_items?: number
    skipped_due_budget?: number
  }
}

export type DailyResult = {
  report: {
    title: string
    date: string
    source?: string
    sources?: string[]
    stats: {
      unique_items: number
      total_query_hits: number
      query_count: number
    }
    queries?: Array<{
      normalized_query?: string
      raw_query?: string
      top_items?: SearchItem[]
    }>
    global_top: SearchItem[]
    llm_analysis?: LLMAnalysis
    judge?: JudgeSummary
  }
  markdown: string
  markdown_path?: string | null
  json_path?: string | null
}

export type WorkflowPhase = "idle" | "searching" | "searched" | "reporting" | "reported" | "error"

export type WorkflowConfig = {
  enableLLM: boolean
  enableJudge: boolean
  useSummary: boolean
  useTrends: boolean
  useInsight: boolean
  useRelevance: boolean
  useArxiv: boolean
  useVenue: boolean
  usePapersCool: boolean
  useArxivApi: boolean
  useHFDaily: boolean
  saveDaily: boolean
  topK: number
  topN: number
  showPerBranch: number
  judgeRuns: number
  judgeMaxItems: number
  judgeTokenBudget: number
  outputDir: string
}

const DEFAULT_CONFIG: WorkflowConfig = {
  enableLLM: true,
  enableJudge: true,
  useSummary: true,
  useTrends: true,
  useInsight: true,
  useRelevance: true,
  useArxiv: true,
  useVenue: true,
  usePapersCool: true,
  useArxivApi: true,
  useHFDaily: true,
  saveDaily: true,
  topK: 5,
  topN: 10,
  showPerBranch: 25,
  judgeRuns: 1,
  judgeMaxItems: 20,
  judgeTokenBudget: 0,
  outputDir: "./reports/dailypaper",
}

interface WorkflowState {
  /* Persisted results */
  searchResult: SearchResult | null
  dailyResult: DailyResult | null
  phase: WorkflowPhase
  analyzeLog: string[]
  lastUpdated: string | null
  notifyEmail: string
  notifyEnabled: boolean
  resendEnabled: boolean
  config: WorkflowConfig

  /* Actions */
  setSearchResult: (result: SearchResult) => void
  setDailyResult: (result: DailyResult | null) => void
  updateDailyResult: (updater: (prev: DailyResult) => DailyResult) => void
  setPhase: (phase: WorkflowPhase) => void
  addAnalyzeLog: (line: string) => void
  clearAnalyzeLog: () => void
  setNotifyEmail: (email: string) => void
  setNotifyEnabled: (enabled: boolean) => void
  setResendEnabled: (enabled: boolean) => void
  updateConfig: (patch: Partial<WorkflowConfig>) => void
  clearAll: () => void
}

export const useWorkflowStore = create<WorkflowState>()(
  persist(
    (set, get) => ({
      searchResult: null,
      dailyResult: null,
      phase: "idle",
      analyzeLog: [],
      lastUpdated: null,
      notifyEmail: "",
      notifyEnabled: false,
      resendEnabled: false,
      config: { ...DEFAULT_CONFIG },

      setSearchResult: (result) =>
        set({ searchResult: result, lastUpdated: new Date().toISOString() }),

      setDailyResult: (result) =>
        set({ dailyResult: result, lastUpdated: new Date().toISOString() }),

      updateDailyResult: (updater) => {
        const prev = get().dailyResult
        if (prev) {
          set({ dailyResult: updater(prev), lastUpdated: new Date().toISOString() })
        }
      },

      setPhase: (phase) => set({ phase }),

      addAnalyzeLog: (line) =>
        set((s) => ({ analyzeLog: [...s.analyzeLog, line] })),

      clearAnalyzeLog: () => set({ analyzeLog: [] }),

      setNotifyEmail: (email) => set({ notifyEmail: email }),

      setNotifyEnabled: (enabled) => set({ notifyEnabled: enabled }),

      setResendEnabled: (enabled) => set({ resendEnabled: enabled }),

      updateConfig: (patch) =>
        set((s) => ({ config: { ...s.config, ...patch } })),

      clearAll: () =>
        set({
          searchResult: null,
          dailyResult: null,
          phase: "idle",
          analyzeLog: [],
          lastUpdated: null,
        }),
    }),
    {
      name: "paperbot-workflow",
      partialize: (state) => ({
        searchResult: state.searchResult,
        dailyResult: state.dailyResult,
        phase: state.phase === "searching" || state.phase === "reporting" ? "idle" : state.phase,
        analyzeLog: state.analyzeLog.slice(-50),
        lastUpdated: state.lastUpdated,
        notifyEmail: state.notifyEmail,
        notifyEnabled: state.notifyEnabled,
        resendEnabled: state.resendEnabled,
        config: state.config,
      }),
    },
  ),
)
