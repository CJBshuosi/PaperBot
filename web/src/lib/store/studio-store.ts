import { create } from 'zustand'

// Agent Action Types
export type ActionType = 'thinking' | 'file_change' | 'function_call' | 'mcp_call' | 'error' | 'complete' | 'text'

export interface AgentAction {
    id: string
    type: ActionType
    timestamp: Date
    content: string
    metadata?: {
        // For file_change
        filename?: string
        linesAdded?: number
        linesDeleted?: number
        diff?: string
        oldContent?: string
        newContent?: string
        // For function_call
        functionName?: string
        params?: Record<string, unknown>
        result?: unknown
        // For mcp_call
        mcpServer?: string
        mcpTool?: string
        mcpResult?: unknown
        // For chat messages
        role?: 'user' | 'assistant'
        mode?: 'Code' | 'Plan' | 'Ask'
        model?: string
    }
}

export interface Task {
    id: string
    name: string
    status: 'running' | 'completed' | 'pending' | 'error'
    actions: AgentAction[]
    createdAt: Date
}

export type GenCodeResult = {
    success?: boolean
    outputDir?: string
    files?: Array<{ name: string; lines: number; purpose: string }>
    blueprint?: { architectureType?: string; domain?: string }
    verificationPassed?: boolean
}

export type PaperDraft = {
    title: string
    abstract: string
    methodSection: string
}

// Studio Paper - represents a paper being reproduced
export type StudioPaperStatus = 'draft' | 'generating' | 'ready' | 'running' | 'completed' | 'error'

export interface StudioPaper {
    id: string
    title: string
    abstract: string
    methodSection?: string

    // Reproduction state
    status: StudioPaperStatus
    outputDir?: string
    lastGenCodeResult?: GenCodeResult

    // Workspace confirmation - must be confirmed before operations
    workspaceConfirmed?: boolean

    // Timestamps
    createdAt: string
    updatedAt: string

    // Linked runs
    taskIds: string[]
}

const STORAGE_KEY = 'paperbot-studio-papers'

function generateId(): string {
    return `paper-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
}

function loadPapersFromStorage(): StudioPaper[] {
    if (typeof window === 'undefined') return []
    try {
        const stored = localStorage.getItem(STORAGE_KEY)
        if (stored) {
            return JSON.parse(stored) as StudioPaper[]
        }
    } catch (e) {
        console.error('Failed to load papers from localStorage:', e)
    }
    return []
}

function savePapersToStorage(papers: StudioPaper[]): void {
    if (typeof window === 'undefined') return
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(papers))
    } catch (e) {
        console.error('Failed to save papers to localStorage:', e)
    }
}

interface StudioState {
    tasks: Task[]
    activeTaskId: string | null
    selectedFileForDiff: string | null
    paperDraft: PaperDraft
    lastGenCodeResult: GenCodeResult | null
    workspaceSnapshotId: number | null

    // Actions
    addTask: (name: string) => string
    updateTaskStatus: (taskId: string, status: Task['status']) => void
    addAction: (taskId: string, action: Omit<AgentAction, 'id' | 'timestamp'>) => void
    setActiveTask: (taskId: string | null) => void
    setSelectedFileForDiff: (filename: string | null) => void
    setPaperDraft: (partial: Partial<PaperDraft>) => void
    setLastGenCodeResult: (result: GenCodeResult | null) => void
    setWorkspaceSnapshotId: (snapshotId: number | null) => void
}

export const useStudioStore = create<StudioState>((set, _get) => ({
    tasks: [],
    activeTaskId: null,
    selectedFileForDiff: null,
    paperDraft: { title: "", abstract: "", methodSection: "" },
    lastGenCodeResult: null,
    workspaceSnapshotId: null,

    addTask: (name) => {
        const id = `task-${Date.now()}`
        set(state => ({
            tasks: [...state.tasks, {
                id,
                name,
                status: 'running',
                actions: [],
                createdAt: new Date()
            }],
            activeTaskId: id
        }))
        return id
    },

    updateTaskStatus: (taskId, status) => {
        set(state => ({
            tasks: state.tasks.map(t =>
                t.id === taskId ? { ...t, status } : t
            )
        }))
    },

    addAction: (taskId, action) => {
        const newAction: AgentAction = {
            ...action,
            id: `action-${Date.now()}-${Math.random().toString(36).slice(2)}`,
            timestamp: new Date()
        }
        set(state => ({
            tasks: state.tasks.map(t =>
                t.id === taskId
                    ? { ...t, actions: [...t.actions, newAction] }
                    : t
            )
        }))
    },

    setActiveTask: (taskId) => set({ activeTaskId: taskId }),
    setSelectedFileForDiff: (filename) => set({ selectedFileForDiff: filename }),

    setPaperDraft: (partial) => set((state) => ({
        paperDraft: { ...state.paperDraft, ...partial }
    })),

    setLastGenCodeResult: (result) => set({ lastGenCodeResult: result }),
    setWorkspaceSnapshotId: (snapshotId) => set({ workspaceSnapshotId: snapshotId }),
}))
