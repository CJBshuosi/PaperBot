"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Textarea } from "@/components/ui/textarea"
import { GenCodeResult, useStudioStore, AgentAction } from "@/lib/store/studio-store"
import { useProjectContext } from "@/lib/store/project-context"
import { readSSE } from "@/lib/sse"
import { CodeBlock } from "@/components/ai-elements"
import { DiffModal } from "./DiffViewer"
import { WorkspaceSetupDialog } from "./WorkspaceSetupDialog"
import { cn } from "@/lib/utils"
import {
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
    X,
    Save,
    Send,
    Paperclip,
    Code,
    User,
    MessageSquare,
    Folder,
} from "lucide-react"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import Editor from "@monaco-editor/react"
import { useTheme } from "next-themes"

type StepStatus = "idle" | "running" | "success" | "error"
type Mode = "Code" | "Plan" | "Ask"

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

    // Handle chat messages with role metadata
    const isUserMessage = action.metadata?.role === "user"
    const isAssistantMessage = action.metadata?.role === "assistant"

    const iconKey = action.metadata?.functionName || action.type
    let Icon = actionIcons[iconKey] || actionIcons[action.type] || Bot
    let colors = actionColors[iconKey] || actionColors[action.type] || actionColors.text

    // Override for chat messages
    if (isUserMessage) {
        Icon = User
        colors = { bg: "bg-blue-50 dark:bg-blue-950/30", text: "text-blue-600 dark:text-blue-400", border: "border-blue-200 dark:border-blue-800" }
    } else if (isAssistantMessage) {
        Icon = Bot
        colors = { bg: "bg-emerald-50 dark:bg-emerald-950/30", text: "text-emerald-600 dark:text-emerald-400", border: "border-emerald-200 dark:border-emerald-800" }
    }

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
                        ) : isUserMessage ? (
                            <div className="space-y-1">
                                <span className="text-[10px] font-medium text-muted-foreground">You</span>
                                <p className="text-sm text-foreground whitespace-pre-wrap leading-relaxed">{action.content}</p>
                            </div>
                        ) : isAssistantMessage ? (
                            <div className="space-y-1">
                                <div className="flex items-center gap-2">
                                    <span className="text-[10px] font-medium text-muted-foreground">Claude</span>
                                    {action.metadata?.mode && (
                                        <span className="text-[9px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                                            {action.metadata.mode}
                                        </span>
                                    )}
                                </div>
                                <p className="text-sm text-foreground whitespace-pre-wrap leading-relaxed">{action.content}</p>
                            </div>
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

export function ReproductionLog() {
    const { theme } = useTheme()
    const {
        papers,
        tasks,
        activeTaskId,
        selectedPaperId,
        lastGenCodeResult,
        addTask,
        addAction,
        updateTaskStatus,
        setLastGenCodeResult,
        updatePaper,
        selectPaper,
    } = useStudioStore()

    const { files, activeFile, updateFile, setActiveFile } = useProjectContext()
    const activeFileData = activeFile ? files[activeFile] : null

    const selectedPaper = useMemo(() =>
        selectedPaperId ? papers.find(p => p.id === selectedPaperId) ?? null : null,
        [papers, selectedPaperId]
    )

    const [status, setStatus] = useState<StepStatus>("idle")
    const runIdRef = useRef<string | null>(null)
    const [mode, setMode] = useState<Mode>("Code")
    const [model, setModel] = useState("claude-sonnet-4-5")
    const [lastError, setLastError] = useState<string | null>(null)
    const [diffAction, setDiffAction] = useState<AgentAction | null>(null)
    const [saving, setSaving] = useState(false)
    const [messageInput, setMessageInput] = useState("")
    const [chatHistory, setChatHistory] = useState<Array<{ role: string; content: string }>>([])
    const [streamingContent, setStreamingContent] = useState("")
    const [cliStatus, setCliStatus] = useState<{ available: boolean; version?: string } | null>(null)
    const [showWorkspaceSetup, setShowWorkspaceSetup] = useState(false)

    // Check Claude CLI status on mount
    useEffect(() => {
        fetch("/api/studio/status")
            .then(res => res.json())
            .then(data => {
                setCliStatus({
                    available: data.claude_cli === true,
                    version: data.claude_version,
                })
            })
            .catch(() => {
                setCliStatus({ available: false })
            })
    }, [])

    // Show workspace setup dialog when selecting an unconfirmed paper
    useEffect(() => {
        if (selectedPaper && !selectedPaper.workspaceConfirmed) {
            setShowWorkspaceSetup(true)
        } else {
            setShowWorkspaceSetup(false)
        }
    }, [selectedPaper?.id, selectedPaper?.workspaceConfirmed])

    const handleWorkspaceConfirm = (directory: string) => {
        if (selectedPaperId) {
            updatePaper(selectedPaperId, {
                outputDir: directory,
                workspaceConfirmed: true,
            })
        }
        setShowWorkspaceSetup(false)
    }

    const handleWorkspaceCancel = () => {
        setShowWorkspaceSetup(false)
        // Optionally deselect the paper if user cancels
        // selectPaper(null)
    }

    const activeTask = tasks.find(t => t.id === activeTaskId)
    const projectDir = selectedPaper?.outputDir || lastGenCodeResult?.outputDir || null

    // Can only run operations if workspace is confirmed
    const hasValidPaper = (selectedPaper?.title.trim().length ?? 0) > 0 && (selectedPaper?.abstract.trim().length ?? 0) > 0
    const isWorkspaceReady = selectedPaper?.workspaceConfirmed === true
    const canRun = hasValidPaper && isWorkspaceReady
    const isBusy = status === "running"

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

    const runPaper2Code = async () => {
        if (!selectedPaper || !canRun || isBusy) return

        setStatus("running")
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
                    if (selectedPaperId && outputDir) {
                        updatePaper(selectedPaperId, { status: 'ready', outputDir })
                    }
                    setStatus("success")
                } else if (evt?.type === "error") {
                    addAction(taskId, { type: "error", content: evt.message || "Run failed" })
                    updateTaskStatus(taskId, "error")
                    if (selectedPaperId) updatePaper(selectedPaperId, { status: 'error' })
                    setLastError(evt.message || "Run failed")
                    setStatus("error")
                    return
                }
            }
        } catch (e) {
            const message = e instanceof Error ? e.message : String(e)
            addAction(taskId, { type: "error", content: message })
            updateTaskStatus(taskId, "error")
            if (selectedPaperId) updatePaper(selectedPaperId, { status: 'error' })
            setLastError(message)
            setStatus("error")
        }
    }

    const handleSendMessage = async () => {
        if (!messageInput.trim() || isBusy) return

        const userMessage = messageInput.trim()
        setMessageInput("")
        setStatus("running")
        setLastError(null)
        setStreamingContent("")

        // Create task for this chat interaction
        const taskId = addTask(`${mode} — ${userMessage.slice(0, 40)}${userMessage.length > 40 ? "…" : ""}`)
        addAction(taskId, { type: "text", content: userMessage, metadata: { role: "user" } })
        updateTaskStatus(taskId, "running")

        // Add to history
        const newHistory = [...chatHistory, { role: "user", content: userMessage }]
        setChatHistory(newHistory)

        try {
            const res = await fetch("/api/studio/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: userMessage,
                    mode,
                    model,
                    paper: selectedPaper ? {
                        title: selectedPaper.title,
                        abstract: selectedPaper.abstract,
                        method_section: selectedPaper.methodSection,
                    } : undefined,
                    project_dir: projectDir,
                    history: chatHistory.slice(-10), // Keep last 10 messages for context
                }),
            })

            if (!res.ok || !res.body) {
                throw new Error(`Failed to start chat (${res.status})`)
            }

            let fullContent = ""
            for await (const evt of readSSE(res.body)) {
                if (evt?.type === "progress") {
                    const data = (evt.data ?? {}) as { delta?: string; content?: string; phase?: string; message?: string }
                    if (data.delta) {
                        fullContent += data.delta
                        setStreamingContent(fullContent)
                    } else if (data.message) {
                        addAction(taskId, { type: "thinking", content: data.message })
                    }
                } else if (evt?.type === "result") {
                    const data = (evt.data ?? {}) as { content?: string }
                    fullContent = data.content || fullContent
                    addAction(taskId, { type: "text", content: fullContent, metadata: { role: "assistant", mode, model } })
                    setChatHistory([...newHistory, { role: "assistant", content: fullContent }])
                    updateTaskStatus(taskId, "completed")
                    setStreamingContent("")
                    setStatus("success")
                } else if (evt?.type === "error") {
                    addAction(taskId, { type: "error", content: evt.message || "Chat failed" })
                    updateTaskStatus(taskId, "error")
                    setLastError(evt.message || "Chat failed")
                    setStatus("error")
                    return
                }
            }
        } catch (e) {
            const message = e instanceof Error ? e.message : String(e)
            addAction(taskId, { type: "error", content: message })
            updateTaskStatus(taskId, "error")
            setLastError(message)
            setStatus("error")
        }
    }

    return (
        <div className="h-full flex flex-col min-w-0 min-h-0 bg-background">
            {/* Simplified Action Bar */}
            <div className="px-4 py-2 flex items-center gap-2 shrink-0 border-b">
                <button
                    onClick={runPaper2Code}
                    disabled={!canRun || isBusy}
                    className="px-4 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors inline-flex items-center gap-2"
                >
                    <Sparkles className="h-4 w-4" />
                    Generate code
                </button>
            </div>

            {/* Error banner */}
            {lastError && (
                <div className="px-4 py-2 flex items-start gap-2 shrink-0 bg-red-50 dark:bg-red-950/30 text-red-600 dark:text-red-400">
                    <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
                    <span className="text-xs">{lastError}</span>
                </div>
            )}

            {/* Main content area */}
            <div className="flex-1 min-h-0 overflow-hidden">
                {activeFileData ? (
                    /* File Viewer */
                    <div className="h-full flex flex-col">
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
                                    onClick={() => setActiveFile("")}
                                    className="p-1.5 rounded hover:bg-muted transition-colors"
                                    title="Close"
                                >
                                    <X className="h-4 w-4" />
                                </button>
                            </div>
                        </div>
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
                    /* Timeline */
                    <ScrollArea className="h-full">
                        <div className="p-4">
                            {!activeTask || activeTask.actions.length === 0 ? (
                                <div className="flex flex-col items-center justify-center text-muted-foreground py-20 space-y-4">
                                    <div className="w-16 h-16 rounded-full bg-muted/50 flex items-center justify-center">
                                        <Sparkles className="h-8 w-8 opacity-30" />
                                    </div>
                                    <div className="text-center space-y-2">
                                        <p className="font-medium">
                                            {selectedPaper && !selectedPaper.workspaceConfirmed
                                                ? "Set up workspace"
                                                : "Ready to reproduce"}
                                        </p>
                                        <p className="text-xs max-w-[280px]">
                                            {!selectedPaper
                                                ? "Select or create a paper to get started"
                                                : !selectedPaper.workspaceConfirmed
                                                    ? "Confirm your workspace directory to start coding"
                                                    : "Click Generate code or send a message to get started"}
                                        </p>
                                        {selectedPaper && !selectedPaper.workspaceConfirmed && (
                                            <Button
                                                variant="outline"
                                                size="sm"
                                                onClick={() => setShowWorkspaceSetup(true)}
                                                className="mt-2"
                                            >
                                                <Folder className="h-4 w-4 mr-2" />
                                                Set Up Workspace
                                            </Button>
                                        )}
                                    </div>
                                </div>
                            ) : (
                                <div className="space-y-0">
                                    {activeTask.actions.map((action, index) => (
                                        <ActionItem
                                            key={action.id}
                                            action={action}
                                            onViewDiff={setDiffAction}
                                            isLast={index === activeTask.actions.length - 1 && !streamingContent}
                                        />
                                    ))}
                                    {/* Streaming response indicator */}
                                    {streamingContent && (
                                        <div className="relative flex gap-2.5">
                                            <div className="relative z-10 w-5 h-5 flex items-center justify-center shrink-0 rounded-md border bg-purple-50 dark:bg-purple-950/30 border-purple-200 dark:border-purple-800">
                                                <Loader2 className="h-2.5 w-2.5 text-purple-600 dark:text-purple-400 animate-spin" />
                                            </div>
                                            <div className="flex-1 min-w-0 pb-3">
                                                <p className="text-xs text-foreground/90 whitespace-pre-wrap leading-relaxed">
                                                    {streamingContent}
                                                    <span className="inline-block w-1.5 h-3.5 bg-foreground/50 animate-pulse ml-0.5" />
                                                </p>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    </ScrollArea>
                )}
            </div>

            {/* Rich Input Area - CodePilot Style */}
            <div className="border-t p-4 shrink-0">
                <div className="border rounded-xl bg-muted/30 overflow-hidden">
                    <Textarea
                        value={messageInput}
                        onChange={(e) => setMessageInput(e.target.value)}
                        placeholder="Message Claude..."
                        className="border-0 bg-transparent resize-none min-h-[60px] focus-visible:ring-0 px-4 py-3"
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && !e.shiftKey) {
                                e.preventDefault()
                                handleSendMessage()
                            }
                        }}
                    />
                    <div className="px-3 py-2 flex items-center justify-between border-t bg-background/50">
                        <div className="flex items-center gap-2">
                            {/* Paper attachment indicator */}
                            {selectedPaper && (
                                <div className="flex items-center gap-1.5 px-2 py-1 bg-muted rounded-md text-xs text-muted-foreground">
                                    <FileText className="h-3.5 w-3.5" />
                                    <span className="max-w-[150px] truncate">{selectedPaper.title}</span>
                                </div>
                            )}
                            {/* Mode selector */}
                            <Select value={mode} onValueChange={(v) => setMode(v as Mode)}>
                                <SelectTrigger className="h-7 w-[90px] text-xs border-0 bg-muted">
                                    <Code className="h-3.5 w-3.5 mr-1" />
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="Code">Code</SelectItem>
                                    <SelectItem value="Plan">Plan</SelectItem>
                                    <SelectItem value="Ask">Ask</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="flex items-center gap-2">
                            {/* CLI Status indicator */}
                            {cliStatus && (
                                <div
                                    className={cn(
                                        "flex items-center gap-1 px-2 py-1 rounded text-[10px]",
                                        cliStatus.available
                                            ? "bg-emerald-100 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-400"
                                            : "bg-amber-100 dark:bg-amber-950/30 text-amber-700 dark:text-amber-400"
                                    )}
                                    title={cliStatus.available ? `Claude CLI ${cliStatus.version || ''}` : "Using Anthropic API"}
                                >
                                    <Terminal className="h-3 w-3" />
                                    {cliStatus.available ? "CLI" : "API"}
                                </div>
                            )}
                            {/* Model selector */}
                            <Select value={model} onValueChange={setModel}>
                                <SelectTrigger className="h-7 w-[130px] text-xs border-0 bg-muted">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="claude-sonnet-4-5">Sonnet 4.5</SelectItem>
                                    <SelectItem value="claude-opus-4-5">Opus 4.5</SelectItem>
                                    <SelectItem value="claude-haiku-4-5">Haiku 4.5</SelectItem>
                                </SelectContent>
                            </Select>
                            {/* Send button */}
                            <Button
                                size="icon"
                                className="h-8 w-8 rounded-full"
                                onClick={handleSendMessage}
                                disabled={!messageInput.trim() || isBusy}
                            >
                                <Send className="h-4 w-4" />
                            </Button>
                        </div>
                    </div>
                </div>
            </div>

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

            {/* Workspace Setup Dialog */}
            {selectedPaper && (
                <WorkspaceSetupDialog
                    paper={selectedPaper}
                    open={showWorkspaceSetup}
                    onConfirm={handleWorkspaceConfirm}
                    onCancel={handleWorkspaceCancel}
                />
            )}
        </div>
    )
}
