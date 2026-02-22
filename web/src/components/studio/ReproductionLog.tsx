"use client"

import { useMemo, useRef, useState } from "react"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { GenCodeResult, useStudioStore, AgentAction } from "@/lib/store/studio-store"
import { useProjectContext } from "@/lib/store/project-context"
import { readSSE } from "@/lib/sse"
import { CodeBlock } from "@/components/ai-elements"
import { DiffModal } from "./DiffViewer"
import { cn } from "@/lib/utils"
import {
    Play,
    Sparkles,
    CheckCircle2,
    AlertCircle,
    FileText,
    Bot,
    FileCode,
    Wrench,
    Terminal,
    ChevronDown,
    ChevronRight,
    Clock,
    Loader2,
    Zap,
    Plus,
    X,
    Save,
} from "lucide-react"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog"
import Editor from "@monaco-editor/react"
import { useTheme } from "next-themes"

type StepStatus = "idle" | "running" | "success" | "error"
type Executor = "openai_ci"

const actionIcons: Record<string, React.ElementType> = {
    thinking: Sparkles,
    file_change: FileCode,
    function_call: Wrench,
    error: AlertCircle,
    complete: CheckCircle2,
    text: Bot,
    run_command: Terminal,
}

const actionColors: Record<string, { bg: string; text: string; border: string }> = {
    thinking: { bg: "bg-purple-50 dark:bg-purple-950/30", text: "text-purple-600 dark:text-purple-400", border: "border-purple-200 dark:border-purple-800" },
    file_change: { bg: "bg-blue-50 dark:bg-blue-950/30", text: "text-blue-600 dark:text-blue-400", border: "border-blue-200 dark:border-blue-800" },
    function_call: { bg: "bg-orange-50 dark:bg-orange-950/30", text: "text-orange-600 dark:text-orange-400", border: "border-orange-200 dark:border-orange-800" },
    error: { bg: "bg-red-50 dark:bg-red-950/30", text: "text-red-600 dark:text-red-400", border: "border-red-200 dark:border-red-800" },
    complete: { bg: "bg-green-50 dark:bg-green-950/30", text: "text-green-600 dark:text-green-400", border: "border-green-200 dark:border-green-800" },
    text: { bg: "bg-muted/50", text: "text-foreground", border: "border-border" },
}

function formatTime(date: Date): string {
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

interface ActionItemProps {
    action: AgentAction
    onViewDiff: (action: AgentAction) => void
    isLast: boolean
}

function ActionItem({ action, onViewDiff, isLast }: ActionItemProps) {
    const [expanded, setExpanded] = useState(false)
    const iconKey = action.metadata?.functionName || action.type
    const Icon = actionIcons[iconKey] || actionIcons[action.type] || Bot
    const colors = actionColors[iconKey] || actionColors[action.type] || actionColors.text

    const hasExpandableContent = Boolean(action.metadata?.params || action.metadata?.result)
    const stringifyPayload = (payload: unknown): string =>
        typeof payload === "string" ? payload : JSON.stringify(payload, null, 2) || ""

    return (
        <div className="relative flex gap-2.5">
            {!isLast && (
                <div className="absolute left-2.5 top-6 bottom-0 w-px bg-border" />
            )}

            <div className={cn(
                "relative z-10 w-5 h-5 flex items-center justify-center shrink-0 rounded-md border",
                colors.bg, colors.border
            )}>
                <Icon className={cn("h-2.5 w-2.5", colors.text)} />
            </div>

            <div className="flex-1 min-w-0 pb-3">
                <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                        {action.type === 'file_change' && action.metadata?.filename ? (
                            <div className="space-y-0.5">
                                <div className="flex items-center gap-2 flex-wrap">
                                    <button
                                        onClick={() => onViewDiff(action)}
                                        className={cn("font-mono text-xs hover:underline", colors.text)}
                                    >
                                        {action.metadata.filename}
                                    </button>
                                    <span className="text-[10px] px-1 py-0.5 rounded bg-muted">
                                        <span className="text-green-600 dark:text-green-400">+{action.metadata.linesAdded || 0}</span>
                                        <span className="text-muted-foreground mx-0.5">/</span>
                                        <span className="text-red-600 dark:text-red-400">-{action.metadata.linesDeleted || 0}</span>
                                    </span>
                                </div>
                            </div>
                        ) : action.type === 'function_call' && action.metadata?.functionName ? (
                            <div className="space-y-0.5">
                                <div className="flex items-center gap-2">
                                    <code className={cn("text-[10px] font-mono px-1 py-0.5 rounded", colors.bg, colors.text)}>
                                        {action.metadata.functionName}()
                                    </code>
                                    {hasExpandableContent && (
                                        <button
                                            onClick={() => setExpanded(!expanded)}
                                            className="text-muted-foreground hover:text-foreground transition-colors"
                                        >
                                            {expanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                                        </button>
                                    )}
                                </div>
                                {expanded && (
                                    <div className="mt-1.5 space-y-1.5">
                                        {Boolean(action.metadata.params) && (
                                            <CodeBlock title="Args" code={stringifyPayload(action.metadata.params)} />
                                        )}
                                        {Boolean(action.metadata.result) && (
                                            <CodeBlock title="Result" code={stringifyPayload(action.metadata.result)} />
                                        )}
                                    </div>
                                )}
                            </div>
                        ) : action.type === 'error' ? (
                            <div className={cn("text-xs rounded-md border px-2 py-1.5", colors.bg, colors.border)}>
                                <span className={colors.text}>{action.content}</span>
                            </div>
                        ) : action.type === 'complete' ? (
                            <span className={cn("text-xs font-medium", colors.text)}>Completed</span>
                        ) : (
                            <p className="text-xs text-foreground/90 whitespace-pre-wrap leading-relaxed">{action.content}</p>
                        )}
                    </div>

                    <div className="flex items-center gap-1 text-[9px] text-muted-foreground shrink-0">
                        <Clock className="h-2 w-2" />
                        {formatTime(action.timestamp)}
                    </div>
                </div>
            </div>
        </div>
    )
}

function StatusBadge({ status }: { status: StepStatus }) {
    const props = useMemo(() => {
        if (status === "running") return { label: "running", className: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300", icon: Loader2, animate: true }
        if (status === "success") return { label: "success", className: "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300", icon: CheckCircle2, animate: false }
        if (status === "error") return { label: "error", className: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300", icon: AlertCircle, animate: false }
        return { label: "idle", className: "bg-muted text-muted-foreground", icon: null, animate: false }
    }, [status])

    return (
        <Badge variant="secondary" className={cn("text-[10px] h-5", props.className)}>
            {props.icon && <props.icon className={cn("h-3 w-3 mr-1", props.animate && "animate-spin")} />}
            {props.label}
        </Badge>
    )
}

export function ReproductionLog() {
    const { theme } = useTheme()
    const {
        papers,
        tasks,
        activeTaskId,
        selectedPaperId,
        lastGenCodeResult,
        addPaper,
        selectPaper,
        addTask,
        addAction,
        updateTaskStatus,
        setLastGenCodeResult,
        updatePaper,
    } = useStudioStore()

    const { files, activeFile, updateFile } = useProjectContext()
    const activeFileData = activeFile ? files[activeFile] : null

    const selectedPaper = useMemo(() =>
        selectedPaperId ? papers.find(p => p.id === selectedPaperId) ?? null : null,
        [papers, selectedPaperId]
    )
    const [status, setStatus] = useState<StepStatus>("idle")
    const runIdRef = useRef<string | null>(null)
    const executor: Executor = "openai_ci"
    const allowNetwork = false
    const [ciModel, setCiModel] = useState("gpt-4o")
    const [pipelineRunning, setPipelineRunning] = useState(false)
    const pipelineRunningRef = useRef(false)
    const [lastError, setLastError] = useState<string | null>(null)
    const [diffAction, setDiffAction] = useState<AgentAction | null>(null)
    const [newPaperOpen, setNewPaperOpen] = useState(false)
    const [newTitle, setNewTitle] = useState("")
    const [newAbstract, setNewAbstract] = useState("")
    const [saving, setSaving] = useState(false)

    const [, setStepStatuses] = useState<Record<string, StepStatus>>({
        install: "idle",
        data: "idle",
        train: "idle",
        eval: "idle",
        report: "idle",
    })

    const activeTask = tasks.find(t => t.id === activeTaskId)
    const paperTasks = useMemo(() => {
        if (!selectedPaperId) return tasks
        return tasks.filter(t => t.paperId === selectedPaperId)
    }, [tasks, selectedPaperId])

    const canRun = (selectedPaper?.title.trim().length ?? 0) > 0 && (selectedPaper?.abstract.trim().length ?? 0) > 0
    const projectDir = selectedPaper?.outputDir || lastGenCodeResult?.outputDir || null
    const isBusy = status === "running" || pipelineRunning

    const setPipelineActive = (active: boolean) => {
        pipelineRunningRef.current = active
        setPipelineRunning(active)
    }

    const handleCreatePaper = () => {
        if (newTitle.trim() && newAbstract.trim()) {
            addPaper({ title: newTitle.trim(), abstract: newAbstract.trim() })
            setNewTitle("")
            setNewAbstract("")
            setNewPaperOpen(false)
        }
    }

    const saveActiveFile = async () => {
        if (!projectDir || !activeFile || !activeFileData) return
        setSaving(true)
        setLastError(null)
        try {
            const res = await fetch(`/api/runbook/file`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ project_dir: projectDir, path: activeFileData.name, content: activeFileData.content }),
            })
            if (!res.ok) {
                const text = await res.text()
                throw new Error(`Failed to save (${res.status}): ${text}`)
            }
        } catch (e) {
            setLastError(e instanceof Error ? e.message : String(e))
        } finally {
            setSaving(false)
        }
    }

    const streamRunLogsToTimeline = async (runId: string, taskId: string) => {
        const res = await fetch(`/api/sandbox/runs/${encodeURIComponent(runId)}/logs/stream`, {
            headers: { Accept: "text/event-stream" },
        })
        if (!res.ok || !res.body) {
            addAction(taskId, { type: "error", content: `Failed to stream logs (${res.status})` })
            return
        }

        for await (const evt of readSSE(res.body)) {
            if (evt?.type === "log") {
                const data = (evt.data ?? {}) as { level?: string; message?: string }
                const level = (data.level || "info").toLowerCase()
                const message = data.message || ""
                if (!message) continue
                addAction(taskId, { type: level === "error" ? "error" : "text", content: message })
            }
        }
    }

    const runStep = async (
        stepName: "install" | "data" | "train" | "eval" | "report",
        body: Record<string, unknown>,
        options: { projectDir?: string; pipeline?: boolean } = {}
    ) => {
        const pipeline = options.pipeline === true
        const targetDir = options.projectDir ?? projectDir
        if (!targetDir) return { ok: false, error: "Project directory not set" }
        if (!pipeline && (status === "running" || pipelineRunningRef.current)) return { ok: false, error: "Busy" }
        if (!pipeline) setStatus("running")

        setStepStatuses((prev) => ({ ...prev, [stepName]: "running" }))
        setLastError(null)

        const taskId = addTask(`${stepName} — ${targetDir.split("/").pop()}`)
        addAction(taskId, { type: "thinking", content: `Starting ${stepName}…` })

        try {
            const res = await fetch(`/api/runbook/${stepName}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    project_dir: targetDir,
                    executor,
                    allow_network: allowNetwork,
                    model: ciModel,
                    ...body,
                }),
            })
            if (!res.ok) {
                const text = await res.text()
                throw new Error(`Failed to start ${stepName} (${res.status}): ${text}`)
            }

            const data = (await res.json()) as { run_id?: string; ok?: boolean; path?: string }

            if (stepName === "report") {
                if (data.ok) {
                    setStepStatuses((prev) => ({ ...prev, [stepName]: "success" }))
                    updateTaskStatus(taskId, "completed")
                    addAction(taskId, { type: "complete", content: `Report generated: ${data.path}` })
                    return { ok: true }
                } else {
                    setStepStatuses((prev) => ({ ...prev, [stepName]: "error" }))
                    updateTaskStatus(taskId, "error")
                    addAction(taskId, { type: "error", content: "Report generation failed" })
                    setLastError("Report generation failed")
                    return { ok: false, error: "Report generation failed" }
                }
            }

            if (!data.run_id) throw new Error("No run_id returned")

            addAction(taskId, { type: "thinking", content: `run_id: ${data.run_id}` })
            await streamRunLogsToTimeline(data.run_id, taskId)

            const statusRes = await fetch(`/api/runbook/runs/${encodeURIComponent(data.run_id)}`)
            if (statusRes.ok) {
                const info = (await statusRes.json()) as { status: string; exit_code?: number; error?: string }
                if (info.status === "success") {
                    setStepStatuses((prev) => ({ ...prev, [stepName]: "success" }))
                    updateTaskStatus(taskId, "completed")
                    addAction(taskId, { type: "complete", content: `${stepName} succeeded` })
                    return { ok: true }
                } else {
                    setStepStatuses((prev) => ({ ...prev, [stepName]: "error" }))
                    updateTaskStatus(taskId, "error")
                    const message = info.error || `${stepName} finished with status: ${info.status}`
                    addAction(taskId, { type: "error", content: message })
                    setLastError(message)
                    return { ok: false, error: message }
                }
            } else {
                setStepStatuses((prev) => ({ ...prev, [stepName]: "success" }))
                updateTaskStatus(taskId, "completed")
                return { ok: true }
            }
        } catch (e) {
            const message = e instanceof Error ? e.message : String(e)
            setStepStatuses((prev) => ({ ...prev, [stepName]: "error" }))
            updateTaskStatus(taskId, "error")
            addAction(taskId, { type: "error", content: message })
            setLastError(message)
            return { ok: false, error: message }
        } finally {
            if (!pipeline) setStatus("idle")
        }
    }

    const runPaper2Code = async (options: { pipeline?: boolean } = {}) => {
        const pipeline = options.pipeline === true
        if (!selectedPaper) {
            const error = "Select or create a paper first."
            setLastError(error)
            return { ok: false, error }
        }
        if (!canRun) {
            const error = "Paper needs title and abstract."
            setLastError(error)
            return { ok: false, error }
        }
        if (!pipeline && (status === "running" || pipelineRunningRef.current)) return { ok: false, error: "Busy" }

        if (!pipeline) setStatus("running")
        setLastError(null)

        if (selectedPaperId) {
            updatePaper(selectedPaperId, { status: 'generating' })
        }

        const taskId = addTask(`Paper2Code — ${selectedPaper.title.slice(0, 40)}${selectedPaper.title.length > 40 ? "…" : ""}`)
        addAction(taskId, { type: "thinking", content: "Starting Paper2Code run…" })
        runIdRef.current = null
        let outputDir: string | undefined

        try {
            const res = await fetch("/api/gen-code", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    title: selectedPaper.title,
                    abstract: selectedPaper.abstract,
                    method_section: selectedPaper.methodSection || undefined,
                    use_orchestrator: true,
                    use_rag: true,
                }),
            })

            if (!res.ok || !res.body) {
                throw new Error(`Failed to start run (${res.status})`)
            }

            updateTaskStatus(taskId, "running")

            for await (const evt of readSSE(res.body)) {
                if (evt?.type === "progress") {
                    const data = (evt.data ?? {}) as { phase?: string; message?: string; run_id?: string }
                    if (data.run_id && !runIdRef.current) {
                        runIdRef.current = data.run_id
                    }
                    addAction(taskId, {
                        type: "thinking",
                        content: `${data.phase ? `[${data.phase}] ` : ""}${data.message || "Working…"}`,
                    })
                } else if (evt?.type === "result") {
                    const result = evt.data as GenCodeResult
                    outputDir = result?.outputDir
                    setLastGenCodeResult(result)
                    addAction(taskId, { type: "complete", content: "Run completed" })
                    updateTaskStatus(taskId, "completed")
                    if (!pipeline) setStatus("success")
                } else if (evt?.type === "error") {
                    addAction(taskId, { type: "error", content: evt.message || "Run failed" })
                    updateTaskStatus(taskId, "error")
                    if (selectedPaperId) updatePaper(selectedPaperId, { status: 'error' })
                    const error = evt.message || "Run failed"
                    setLastError(error)
                    if (!pipeline) setStatus("error")
                    return { ok: false, error }
                }
            }
            if (!outputDir) {
                const error = "Paper2Code completed without an output directory."
                setLastError(error)
                if (selectedPaperId) updatePaper(selectedPaperId, { status: 'error' })
                if (!pipeline) setStatus("error")
                return { ok: false, error }
            }
            return { ok: true, outputDir }
        } catch (e) {
            const message = e instanceof Error ? e.message : String(e)
            addAction(taskId, { type: "error", content: message })
            updateTaskStatus(taskId, "error")
            if (selectedPaperId) updatePaper(selectedPaperId, { status: 'error' })
            setLastError(message)
            if (!pipeline) setStatus("error")
            return { ok: false, error: message }
        }
    }

    const runSmoke = async (options: { projectDir?: string; pipeline?: boolean } = {}) => {
        const pipeline = options.pipeline === true
        const targetDir = options.projectDir ?? projectDir
        if (!targetDir) return { ok: false, error: "Project directory not set" }
        if (!pipeline && (status === "running" || pipelineRunningRef.current)) return { ok: false, error: "Busy" }
        if (!pipeline) setStatus("running")

        setLastError(null)
        const taskId = addTask(`Smoke — ${targetDir.split("/").slice(-1)[0]}`)
        addAction(taskId, { type: "thinking", content: `Starting smoke test…` })

        try {
            const res = await fetch("/api/runbook/smoke", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    project_dir: targetDir,
                    executor,
                    allow_network: allowNetwork,
                    model: ciModel,
                }),
            })
            if (!res.ok) {
                const text = await res.text()
                throw new Error(`Failed to start smoke (${res.status}): ${text}`)
            }
            const data = (await res.json()) as { run_id: string }
            addAction(taskId, { type: "thinking", content: `run_id: ${data.run_id}` })

            await streamRunLogsToTimeline(data.run_id, taskId)

            const statusRes = await fetch(`/api/runbook/runs/${encodeURIComponent(data.run_id)}`)
            if (statusRes.ok) {
                const info = (await statusRes.json()) as { status: string; exit_code?: number; error?: string }
                if (info.status === "success") {
                    updateTaskStatus(taskId, "completed")
                    addAction(taskId, { type: "complete", content: `Smoke succeeded` })
                    if (!pipeline) setStatus("success")
                    return { ok: true }
                } else {
                    updateTaskStatus(taskId, "error")
                    const message = info.error || `Smoke finished with status: ${info.status}`
                    addAction(taskId, { type: "error", content: message })
                    setLastError(message)
                    if (!pipeline) setStatus("error")
                    return { ok: false, error: message }
                }
            } else {
                updateTaskStatus(taskId, "completed")
                if (!pipeline) setStatus("success")
                return { ok: true }
            }
        } catch (e) {
            const message = e instanceof Error ? e.message : String(e)
            updateTaskStatus(taskId, "error")
            addAction(taskId, { type: "error", content: message })
            setLastError(message)
            if (!pipeline) setStatus("error")
            return { ok: false, error: message }
        }
    }

    const runPipeline = async () => {
        if (status === "running" || pipelineRunningRef.current) return
        if (!canRun) {
            setLastError("Paper needs title and abstract.")
            return
        }

        setPipelineActive(true)
        setStatus("running")
        setLastError(null)
        setStepStatuses({
            install: "idle",
            data: "idle",
            train: "idle",
            eval: "idle",
            report: "idle",
        })

        if (selectedPaperId) updatePaper(selectedPaperId, { status: 'running' })

        const taskId = addTask(`Full Pipeline — ${selectedPaper?.title.slice(0, 40)}${(selectedPaper?.title.length ?? 0) > 40 ? "…" : ""}`)
        updateTaskStatus(taskId, "running")
        addAction(taskId, { type: "thinking", content: "Starting Paper2Code → Smoke → Install → Train → Eval → Report…" })

        try {
            const paperResult = await runPaper2Code({ pipeline: true })
            if (!paperResult.ok) throw new Error(paperResult.error || "Paper2Code failed")
            const pipelineProjectDir = paperResult.outputDir || projectDir
            if (!pipelineProjectDir) throw new Error("Paper2Code did not return a project directory.")

            addAction(taskId, { type: "thinking", content: "Running smoke..." })
            const smokeResult = await runSmoke({ pipeline: true, projectDir: pipelineProjectDir })
            if (!smokeResult.ok) throw new Error(smokeResult.error || "Smoke failed")

            addAction(taskId, { type: "thinking", content: "Running install..." })
            const installResult = await runStep("install", { pip_cache: true }, { pipeline: true, projectDir: pipelineProjectDir })
            if (!installResult.ok) throw new Error(installResult.error || "Install failed")

            addAction(taskId, { type: "thinking", content: "Running train (mini)..." })
            const trainResult = await runStep("train", { mini_mode: true, max_epochs: 2, max_samples: 100 }, { pipeline: true, projectDir: pipelineProjectDir })
            if (!trainResult.ok) throw new Error(trainResult.error || "Train failed")

            addAction(taskId, { type: "thinking", content: "Running eval..." })
            const evalResult = await runStep("eval", {}, { pipeline: true, projectDir: pipelineProjectDir })
            if (!evalResult.ok) throw new Error(evalResult.error || "Eval failed")

            addAction(taskId, { type: "thinking", content: "Generating report..." })
            const reportResult = await runStep("report", { output_format: "html" }, { pipeline: true, projectDir: pipelineProjectDir })
            if (!reportResult.ok) throw new Error(reportResult.error || "Report failed")

            updateTaskStatus(taskId, "completed")
            addAction(taskId, { type: "complete", content: "Pipeline completed successfully." })
            if (selectedPaperId) updatePaper(selectedPaperId, { status: 'completed' })
            setStatus("success")
        } catch (e) {
            const message = e instanceof Error ? e.message : String(e)
            updateTaskStatus(taskId, "error")
            addAction(taskId, { type: "error", content: message })
            if (selectedPaperId) updatePaper(selectedPaperId, { status: 'error' })
            setLastError(message)
            setStatus("error")
        } finally {
            setPipelineActive(false)
        }
    }

    const openFiles = useMemo(() => Object.values(files), [files])
    const { setActiveFile } = useProjectContext()

    return (
        <div className="h-full flex flex-col min-w-0 min-h-0 bg-background">
            {/* Action buttons + file tabs row */}
            <div className="px-4 py-2.5 flex items-center gap-1.5 shrink-0 border-b overflow-x-auto">
                <button
                    onClick={() => runPaper2Code()}
                    disabled={!canRun || isBusy}
                    className="px-3 py-1.5 text-xs font-medium rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shrink-0"
                >
                    <Sparkles className="h-3.5 w-3.5 mr-1.5 inline" />
                    Paper2Code
                </button>
                <button
                    onClick={() => runSmoke()}
                    disabled={!projectDir || isBusy}
                    className="px-3 py-1.5 text-xs font-medium rounded-md hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed transition-colors shrink-0"
                >
                    Smoke
                </button>
                <button
                    onClick={() => runStep("install", { pip_cache: true })}
                    disabled={!projectDir || isBusy}
                    className="px-3 py-1.5 text-xs font-medium rounded-md hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed transition-colors shrink-0"
                >
                    Install
                </button>
                <button
                    onClick={() => runStep("train", { mini_mode: true, max_epochs: 2, max_samples: 100 })}
                    disabled={!projectDir || isBusy}
                    className="px-3 py-1.5 text-xs font-medium rounded-md hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed transition-colors shrink-0"
                >
                    Train
                </button>
                <button
                    onClick={() => runStep("eval", {})}
                    disabled={!projectDir || isBusy}
                    className="px-3 py-1.5 text-xs font-medium rounded-md hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed transition-colors shrink-0"
                >
                    Eval
                </button>
                <button
                    onClick={() => runStep("report", { output_format: "html" })}
                    disabled={!projectDir || isBusy}
                    className="px-3 py-1.5 text-xs font-medium rounded-md hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed transition-colors shrink-0"
                >
                    Report
                </button>

                <div className="flex-1" />

                <Select value={ciModel} onValueChange={setCiModel}>
                    <SelectTrigger className="h-7 w-[90px] text-xs border-0 bg-muted/50 shrink-0">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="gpt-4o">gpt-4o</SelectItem>
                        <SelectItem value="gpt-4o-mini">gpt-4o-mini</SelectItem>
                    </SelectContent>
                </Select>
            </div>

            {/* Error banner */}
            {lastError && (
                <div className="px-4 py-2 flex items-start gap-2 shrink-0 bg-red-50 dark:bg-red-950/30 text-red-600 dark:text-red-400">
                    <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
                    <span className="text-xs">{lastError}</span>
                </div>
            )}

            {/* Main content area - Timeline or File Viewer */}
            <div className="flex-1 min-h-0 overflow-hidden">
                {activeFileData ? (
                    /* File Viewer - full panel when file is selected */
                    <div className="h-full flex flex-col">
                        {/* File header */}
                        <div className="px-4 py-2 border-b flex items-center justify-between bg-muted/30 shrink-0">
                            <div className="flex items-center gap-2 text-sm">
                                <FileCode className="h-4 w-4 text-muted-foreground" />
                                <span className="font-medium">{activeFileData.name}</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <Button
                                    variant="default"
                                    size="sm"
                                    className="h-7 text-xs"
                                    onClick={saveActiveFile}
                                    disabled={!projectDir || saving}
                                >
                                    <Save className="h-3.5 w-3.5 mr-1" />
                                    {saving ? "Saving..." : "Save"}
                                </Button>
                                <button
                                    onClick={() => {
                                        // Close view: deselect file (file stays in Files panel)
                                        setActiveFile("")
                                    }}
                                    className="p-1.5 rounded hover:bg-muted transition-colors"
                                    title="Close"
                                >
                                    <X className="h-4 w-4" />
                                </button>
                            </div>
                        </div>
                        {/* Monaco Editor */}
                        <div className="flex-1 min-h-0 overflow-hidden">
                            <Editor
                                height="100%"
                                language={activeFileData.language}
                                value={activeFileData.content}
                                theme={theme === "dark" ? "vs-dark" : "light"}
                                onChange={(value) => updateFile(activeFileData.name, value || "")}
                                options={{
                                    minimap: { enabled: false },
                                    fontSize: 13,
                                    lineNumbers: "on",
                                    scrollBeyondLastLine: false,
                                    automaticLayout: true,
                                    padding: { top: 12, bottom: 12 },
                                    fontFamily: "'JetBrains Mono', 'Menlo', 'Monaco', 'Courier New', monospace",
                                }}
                            />
                        </div>
                    </div>
                ) : (
                    /* Timeline - show when no file is selected */
                    <ScrollArea className="h-full">
                <div className="p-4">
                    {!activeTask || activeTask.actions.length === 0 ? (
                        <div className="flex flex-col items-center justify-center text-muted-foreground py-20 space-y-4">
                            <div className="w-16 h-16 rounded-full bg-muted/50 flex items-center justify-center">
                                <Sparkles className="h-8 w-8 opacity-30" />
                            </div>
                            <div className="text-center space-y-2">
                                <p className="font-medium">Ready to reproduce</p>
                                <p className="text-xs max-w-[280px]">
                                    {selectedPaper
                                        ? "Click Paper2Code to generate code from the selected paper"
                                        : "Select or create a paper to get started"}
                                </p>
                            </div>
                            {!selectedPaper && (
                                <div className="flex items-center gap-2 pt-2">
                                    <Select
                                        value={selectedPaperId || ""}
                                        onValueChange={(id) => id && selectPaper(id)}
                                    >
                                        <SelectTrigger className="h-9 w-[200px]">
                                            <SelectValue placeholder="Select a paper..." />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {papers.map(paper => (
                                                <SelectItem key={paper.id} value={paper.id}>
                                                    {paper.title.slice(0, 40)}{paper.title.length > 40 ? "…" : ""}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        className="h-9"
                                        onClick={() => setNewPaperOpen(true)}
                                    >
                                        <Plus className="h-4 w-4 mr-1" />
                                        New
                                    </Button>
                                </div>
                            )}
                        </div>
                    ) : (
                        <div className="space-y-0">
                            {activeTask.actions.map((action, index) => (
                                <ActionItem
                                    key={action.id}
                                    action={action}
                                    onViewDiff={setDiffAction}
                                    isLast={index === activeTask.actions.length - 1}
                                />
                            ))}
                        </div>
                    )}
                    </div>
                    </ScrollArea>
                )}
            </div>

            {/* Minimal footer with paper info */}
            {selectedPaper && (
                <div className="border-t px-4 py-2 flex items-center gap-2 text-xs text-muted-foreground shrink-0">
                    <FileText className="h-3.5 w-3.5" />
                    <span className="truncate">{selectedPaper.title}</span>
                </div>
            )}

            {/* New Paper Dialog */}
            <Dialog open={newPaperOpen} onOpenChange={setNewPaperOpen}>
                <DialogContent className="sm:max-w-md">
                    <DialogHeader>
                        <DialogTitle>New Paper</DialogTitle>
                        <DialogDescription>
                            Add a paper for code reproduction.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 py-2">
                        <div className="space-y-2">
                            <Label htmlFor="title">Title</Label>
                            <Input
                                id="title"
                                value={newTitle}
                                onChange={(e) => setNewTitle(e.target.value)}
                                placeholder="Paper title"
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="abstract">Abstract</Label>
                            <Textarea
                                id="abstract"
                                value={newAbstract}
                                onChange={(e) => setNewAbstract(e.target.value)}
                                placeholder="Paste the paper abstract"
                                className="min-h-[120px]"
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setNewPaperOpen(false)}>
                            Cancel
                        </Button>
                        <Button
                            onClick={handleCreatePaper}
                            disabled={!newTitle.trim() || !newAbstract.trim()}
                        >
                            Add Paper
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Diff Modal */}
            <DiffModal
                isOpen={!!diffAction}
                oldValue={diffAction?.metadata?.oldContent || '// Original file content'}
                newValue={diffAction?.metadata?.newContent || diffAction?.metadata?.diff || '// Modified file content'}
                filename={diffAction?.metadata?.filename}
                onClose={() => setDiffAction(null)}
                onApply={() => setDiffAction(null)}
                onReject={() => setDiffAction(null)}
            />
        </div>
    )
}
