/**
 * @deprecated This component has been replaced by ReproductionLog
 * in the new 3-panel CodePilot-style layout. Kept for reference during transition.
 */
"use client"

import { useMemo, useRef, useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { GenCodeResult, useStudioStore } from "@/lib/store/studio-store"
import { readSSE } from "@/lib/sse"
import { Play, Sparkles, CheckCircle2, AlertCircle, FileText } from "lucide-react"
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"

type StepStatus = "idle" | "running" | "success" | "error"
type Executor = "openai_ci"

function StatusBadge({ status }: { status: StepStatus }) {
  const props = useMemo(() => {
    if (status === "running") return { label: "running", className: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300" }
    if (status === "success") return { label: "success", className: "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300" }
    if (status === "error") return { label: "error", className: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300" }
    return { label: "idle", className: "bg-muted text-muted-foreground" }
  }, [status])

  return (
    <Badge variant="secondary" className={props.className}>
      {props.label}
    </Badge>
  )
}

export function RunbookPanel() {
  const { paperDraft, lastGenCodeResult, addTask, addAction, updateTaskStatus, setLastGenCodeResult } = useStudioStore()
  const [status, setStatus] = useState<StepStatus>("idle")
  const [runId, setRunId] = useState<string | null>(null)
  const runIdRef = useRef<string | null>(null)
  const executor: Executor = "openai_ci"
  const allowNetwork = false  // Code Interpreter has restricted network
  const [ciModel, setCiModel] = useState("gpt-4o")
  const [pipelineRunning, setPipelineRunning] = useState(false)
  const pipelineRunningRef = useRef(false)
  const [lastError, setLastError] = useState<string | null>(null)

  // Step statuses for new pipeline steps
  const [stepStatuses, setStepStatuses] = useState<Record<string, StepStatus>>({
    install: "idle",
    data: "idle",
    train: "idle",
    eval: "idle",
    report: "idle",
  })

  // Detected commands from backend
  const [detectedCommands, setDetectedCommands] = useState<Record<string, {
    detected: boolean
    command: string | null
  }> | null>(null)

  // Train config
  const [trainMiniMode, setTrainMiniMode] = useState(true)
  const [trainMaxEpochs, setTrainMaxEpochs] = useState(2)


  const canRun = paperDraft.title.trim().length > 0 && paperDraft.abstract.trim().length > 0
  const projectDir = lastGenCodeResult?.outputDir || null

  const isBusy = status === "running" || pipelineRunning
  const setPipelineActive = (active: boolean) => {
    pipelineRunningRef.current = active
    setPipelineRunning(active)
  }

  // Detect commands when projectDir changes
  useEffect(() => {
    if (!projectDir) {
      setDetectedCommands(null)
      return
    }
    fetch(`/api/runbook/detect-commands?project_dir=${encodeURIComponent(projectDir)}`)
      .then((res) => res.json())
      .then(setDetectedCommands)
      .catch(() => setDetectedCommands(null))
  }, [projectDir])

  // Generic step runner
  const runStep = async (
    stepName: "install" | "data" | "train" | "eval" | "report",
    body: Record<string, unknown>,
    options: { projectDir?: string; pipeline?: boolean } = {}
  ) => {
    const pipeline = options.pipeline === true
    const targetDir = options.projectDir ?? projectDir
    if (!targetDir) return { ok: false, error: "Project directory not set" }
    if (!pipeline) {
      if (status === "running" || pipelineRunningRef.current) return { ok: false, error: "Busy" }
      setStatus("running")
    }

    setStepStatuses((prev) => ({ ...prev, [stepName]: "running" }))
    setLastError(null)

    const taskId = addTask(`Runbook: ${stepName} — ${targetDir.split("/").pop()}`)
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

      // Report endpoint doesn't return run_id, it's synchronous
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

      // Poll final status
      const statusRes = await fetch(`/api/runbook/runs/${encodeURIComponent(data.run_id)}`)
      if (statusRes.ok) {
        const info = (await statusRes.json()) as { status: string; exit_code?: number; error?: string }
        if (info.status === "success") {
          setStepStatuses((prev) => ({ ...prev, [stepName]: "success" }))
          updateTaskStatus(taskId, "completed")
          addAction(taskId, { type: "complete", content: `${stepName} succeeded (exit_code=${info.exit_code ?? 0})` })
          return { ok: true }
        } else {
          setStepStatuses((prev) => ({ ...prev, [stepName]: "error" }))
          updateTaskStatus(taskId, "error")
          addAction(taskId, { type: "error", content: info.error || `${stepName} finished with status: ${info.status}` })
          const message = info.error || `${stepName} finished with status: ${info.status}`
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
    if (!canRun) {
      const error = "Add Title and Abstract in Blueprint to enable Paper2Code."
      setLastError(error)
      return { ok: false, error }
    }
    if (!pipeline && (status === "running" || pipelineRunningRef.current)) return { ok: false, error: "Busy" }

    if (!pipeline) setStatus("running")
    setLastError(null)
    const taskId = addTask(`Runbook: Paper2Code — ${paperDraft.title.slice(0, 40)}${paperDraft.title.length > 40 ? "…" : ""}`)
    addAction(taskId, { type: "thinking", content: "Starting Paper2Code run…" })
    runIdRef.current = null
    setRunId(null)
    let outputDir: string | undefined

    try {
      const res = await fetch("/api/gen-code", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: paperDraft.title,
          abstract: paperDraft.abstract,
          method_section: paperDraft.methodSection || undefined,
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
            setRunId(data.run_id)
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
          const error = evt.message || "Run failed"
          setLastError(error)
          if (!pipeline) setStatus("error")
          return { ok: false, error }
        }
      }
      if (!outputDir) {
        const error = "Paper2Code completed without an output directory."
        setLastError(error)
        if (!pipeline) setStatus("error")
        return { ok: false, error }
      }
      return { ok: true, outputDir }
    } catch (e) {
      const message = e instanceof Error ? e.message : String(e)
      addAction(taskId, { type: "error", content: message })
      updateTaskStatus(taskId, "error")
      setLastError(message)
      if (!pipeline) setStatus("error")
      return { ok: false, error: message }
    }
    return { ok: false, error: "Paper2Code did not complete." }
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
        const data = (evt.data ?? {}) as { level?: string; message?: string; source?: string }
        const level = (data.level || "info").toLowerCase()
        const message = data.message || ""
        if (!message) continue
        addAction(taskId, { type: level === "error" ? "error" : "text", content: message })
      }
    }
  }

  const runSmoke = async (options: { projectDir?: string; pipeline?: boolean } = {}) => {
    const pipeline = options.pipeline === true
    const targetDir = options.projectDir ?? projectDir
    if (!targetDir) return { ok: false, error: "Project directory not set" }
    if (!pipeline) {
      if (status === "running" || pipelineRunningRef.current) return { ok: false, error: "Busy" }
      setStatus("running")
    }

    setLastError(null)
    const taskId = addTask(`Runbook: Smoke — ${executor} — ${targetDir.split("/").slice(-1)[0]}`)
    addAction(taskId, { type: "thinking", content: `Starting smoke on ${executor}…` })

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
      addAction(taskId, { type: "thinking", content: `Smoke run_id: ${data.run_id}` })

      await streamRunLogsToTimeline(data.run_id, taskId)

      const statusRes = await fetch(`/api/runbook/runs/${encodeURIComponent(data.run_id)}`)
      if (statusRes.ok) {
        const info = (await statusRes.json()) as { status: string; exit_code?: number; error?: string }
        if (info.status === "success") {
          updateTaskStatus(taskId, "completed")
          addAction(taskId, { type: "complete", content: `Smoke succeeded (exit_code=${info.exit_code ?? 0})` })
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
    return { ok: false, error: "Smoke run did not complete." }
  }

  const runPipeline = async () => {
    if (status === "running" || pipelineRunningRef.current) return
    if (!canRun) {
      const error = "Add Title and Abstract in Blueprint to run the full pipeline."
      setLastError(error)
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

    const taskId = addTask(`Runbook: Full pipeline — ${paperDraft.title.slice(0, 40)}${paperDraft.title.length > 40 ? "…" : ""}`)
    updateTaskStatus(taskId, "running")
    addAction(taskId, { type: "thinking", content: "Starting Paper2Code → Smoke → Install → Data → Train → Eval → Report…" })

    try {
      const paperResult = await runPaper2Code({ pipeline: true })
      if (!paperResult.ok) throw new Error(paperResult.error || "Paper2Code failed")
      const pipelineProjectDir = paperResult.outputDir || projectDir
      if (!pipelineProjectDir) throw new Error("Paper2Code did not return a project directory.")

      addAction(taskId, { type: "thinking", content: "Paper2Code complete. Running smoke..." })
      const smokeResult = await runSmoke({ pipeline: true, projectDir: pipelineProjectDir })
      if (!smokeResult.ok) throw new Error(smokeResult.error || "Smoke failed")

      addAction(taskId, { type: "thinking", content: "Running install..." })
      const installResult = await runStep("install", { pip_cache: true }, { pipeline: true, projectDir: pipelineProjectDir })
      if (!installResult.ok) throw new Error(installResult.error || "Install failed")

      if (detectedCommands?.data?.detected) {
        addAction(taskId, { type: "thinking", content: "Running data step..." })
        const dataResult = await runStep("data", {}, { pipeline: true, projectDir: pipelineProjectDir })
        if (!dataResult.ok) throw new Error(dataResult.error || "Data step failed")
      } else {
        setStepStatuses((prev) => ({ ...prev, data: "success" }))
        addAction(taskId, { type: "thinking", content: "Data step skipped (no script detected)." })
      }

      addAction(taskId, { type: "thinking", content: "Running train (mini)..." })
      const trainResult = await runStep(
        "train",
        {
          mini_mode: trainMiniMode,
          max_epochs: trainMaxEpochs,
          max_samples: 100,
        },
        { pipeline: true, projectDir: pipelineProjectDir }
      )
      if (!trainResult.ok) throw new Error(trainResult.error || "Train failed")

      addAction(taskId, { type: "thinking", content: "Running eval..." })
      const evalResult = await runStep("eval", {}, { pipeline: true, projectDir: pipelineProjectDir })
      if (!evalResult.ok) throw new Error(evalResult.error || "Eval failed")

      addAction(taskId, { type: "thinking", content: "Generating report..." })
      const reportResult = await runStep("report", { output_format: "html" }, { pipeline: true, projectDir: pipelineProjectDir })
      if (!reportResult.ok) throw new Error(reportResult.error || "Report failed")

      updateTaskStatus(taskId, "completed")
      addAction(taskId, { type: "complete", content: "Pipeline completed successfully." })
      setStatus("success")
    } catch (e) {
      const message = e instanceof Error ? e.message : String(e)
      updateTaskStatus(taskId, "error")
      addAction(taskId, { type: "error", content: message })
      setLastError(message)
      setStatus("error")
    } finally {
      setPipelineActive(false)
    }
  }

  return (
    <div className="h-full flex flex-col min-w-0 min-h-0 bg-muted/5">
      <div className="border-b px-4 py-3 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 flex items-center justify-between">
        <div className="min-w-0">
          <div className="text-sm font-semibold flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-purple-500" /> Runbook
          </div>
          <div className="text-xs text-muted-foreground truncate">Executable steps that produce evidence.</div>
        </div>
        <StatusBadge status={status} />
      </div>

      <ScrollArea className="flex-1 min-h-0">
        <div className="p-3 space-y-3">
          {lastError && (
            <Card className="border-destructive/40 bg-destructive/5">
              <CardContent className="px-4 py-3 text-xs text-destructive flex items-start gap-2">
                <AlertCircle className="h-4 w-4 mt-0.5" />
                <div className="min-w-0">
                  <div className="font-medium">Last error</div>
                  <div className="break-words">{lastError}</div>
                </div>
              </CardContent>
            </Card>
          )}
          <Card className="py-4">
            <CardHeader className="px-4">
              <CardTitle className="text-sm flex items-center gap-2">
                Execution Backend
              </CardTitle>
              <CardDescription className="text-xs">OpenAI Code Interpreter (Assistants API)</CardDescription>
            </CardHeader>
            <CardContent className="px-4 space-y-3">
              <div className="space-y-1.5">
                <Label className="text-xs" htmlFor="ci-model">Model</Label>
                <Input
                  id="ci-model"
                  list="ci-models"
                  value={ciModel}
                  onChange={(e) => setCiModel(e.target.value)}
                  placeholder="gpt-4o"
                  className="h-8 text-xs"
                />
                <datalist id="ci-models">
                  <option value="gpt-4o" />
                  <option value="gpt-4o-mini" />
                </datalist>
              </div>
              <div className="text-[10px] text-muted-foreground">
                Executes code in OpenAI&apos;s secure sandbox via Assistants API. Requires direct OpenAI API key.
              </div>
            </CardContent>
          </Card>

          <Card className="py-4">
            <CardHeader className="px-4">
              <CardTitle className="text-sm">Auto Run</CardTitle>
              <CardDescription className="text-xs">Paper2Code → Smoke → Install → Data → Train → Eval → Report</CardDescription>
              <CardAction>
                <Button size="sm" className="h-8" onClick={runPipeline} disabled={!canRun || isBusy}>
                  <Play className="h-3.5 w-3.5 mr-2" />
                  {pipelineRunning ? "Running…" : "Run All"}
                </Button>
              </CardAction>
            </CardHeader>
            <CardContent className="px-4 text-xs text-muted-foreground">
              Logs stream to Timeline. The pipeline stops at the first error.
            </CardContent>
          </Card>

          <Card className="py-4">
            <CardHeader className="px-4">
              <CardTitle className="text-sm">Paper2Code</CardTitle>
              <CardDescription className="text-xs">Generate project skeleton and run verification.</CardDescription>
              <CardAction>
                <Button
                  size="sm"
                  className="h-8"
                  onClick={() => runPaper2Code()}
                  disabled={!canRun || isBusy}
                >
                  <Play className="h-3.5 w-3.5 mr-2" />
                  Run
                </Button>
              </CardAction>
            </CardHeader>
            <CardContent className="px-4 space-y-2">
              {!canRun && (
                <div className="text-xs text-muted-foreground">
                  Add <span className="font-medium">Title</span> and <span className="font-medium">Abstract</span> in Blueprint to enable.
                </div>
              )}
              {runId && (
                <div className="text-[11px] text-muted-foreground">
                  run_id: <span className="font-mono">{runId}</span>
                </div>
              )}
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                {status === "success" ? (
                  <>
                    <CheckCircle2 className="h-4 w-4 text-green-500" /> Last run succeeded.
                  </>
                ) : status === "error" ? (
                  <>
                    <AlertCircle className="h-4 w-4 text-red-500" /> Last run failed. Check Timeline.
                  </>
                ) : status === "running" ? (
                  <>Streaming progress to Timeline…</>
                ) : (
                  <>Ready.</>
                )}
              </div>
            </CardContent>
          </Card>

          <Card className="py-4">
            <CardHeader className="px-4">
              <CardTitle className="text-sm">Smoke</CardTitle>
              <CardDescription className="text-xs">Minimal sanity check for the generated project (pip + compileall).</CardDescription>
              <CardAction>
                <Button size="sm" className="h-8" onClick={() => runSmoke()} disabled={!projectDir || isBusy}>
                  <Play className="h-3.5 w-3.5 mr-2" />
                  Run
                </Button>
              </CardAction>
            </CardHeader>
            <CardContent className="px-4 text-xs text-muted-foreground space-y-1">
              {projectDir ? (
                <>
                  <div>
                    Project: <span className="font-mono">{projectDir}</span>
                  </div>
                  <div>
                    Executor: <span className="font-mono">{executor}</span>
                  </div>
                </>
              ) : (
                <div>Run Paper2Code first to get an output directory.</div>
              )}
            </CardContent>
          </Card>

          {/* Install Step */}
          <Card className="py-4">
            <CardHeader className="px-4">
              <CardTitle className="text-sm flex items-center gap-2">
                Install <StatusBadge status={stepStatuses.install} />
              </CardTitle>
              <CardDescription className="text-xs">Install dependencies</CardDescription>
              <CardAction>
                  <Button
                    size="sm"
                    className="h-8"
                    onClick={() => runStep("install", { pip_cache: true })}
                    disabled={!projectDir || isBusy}
                  >
                    <Play className="h-3.5 w-3.5 mr-2" /> Run
                  </Button>
                </CardAction>
            </CardHeader>
            <CardContent className="px-4 text-xs text-muted-foreground">
              {detectedCommands?.install?.command || "pip install -r requirements.txt"}
            </CardContent>
          </Card>

          {/* Data Step */}
          <Card className="py-4">
            <CardHeader className="px-4">
              <CardTitle className="text-sm flex items-center gap-2">
                Data <StatusBadge status={stepStatuses.data} />
              </CardTitle>
              <CardDescription className="text-xs">Prepare dataset</CardDescription>
              <CardAction>
                  <Button
                    size="sm"
                    className="h-8"
                    onClick={() => runStep("data", {})}
                    disabled={!projectDir || isBusy || !detectedCommands?.data?.detected}
                  >
                    <Play className="h-3.5 w-3.5 mr-2" /> Run
                  </Button>
                </CardAction>
            </CardHeader>
            <CardContent className="px-4 text-xs text-muted-foreground">
              {detectedCommands?.data?.command || "No data script detected"}
            </CardContent>
          </Card>

          {/* Train Step */}
          <Card className="py-4">
            <CardHeader className="px-4">
              <CardTitle className="text-sm flex items-center gap-2">
                Train (Mini) <StatusBadge status={stepStatuses.train} />
              </CardTitle>
              <CardDescription className="text-xs">Quick training with limited epochs</CardDescription>
              <CardAction>
                  <Button
                    size="sm"
                    className="h-8"
                    onClick={() =>
                      runStep("train", {
                        mini_mode: trainMiniMode,
                        max_epochs: trainMaxEpochs,
                        max_samples: 100,
                      })
                    }
                    disabled={!projectDir || isBusy}
                  >
                    <Play className="h-3.5 w-3.5 mr-2" /> Run
                  </Button>
                </CardAction>
            </CardHeader>
            <CardContent className="px-4 space-y-2">
              <div className="flex items-center gap-4 text-xs">
                <div className="flex items-center gap-2">
                  <Label className="text-xs">Mini Mode</Label>
                  <Switch checked={trainMiniMode} onCheckedChange={setTrainMiniMode} />
                </div>
                {trainMiniMode && <span className="text-muted-foreground">Epochs: {trainMaxEpochs}</span>}
              </div>
              <div className="text-xs text-muted-foreground">
                {detectedCommands?.train?.command || "python train.py"}
              </div>
            </CardContent>
          </Card>

          {/* Eval Step */}
          <Card className="py-4">
            <CardHeader className="px-4">
              <CardTitle className="text-sm flex items-center gap-2">
                Eval <StatusBadge status={stepStatuses.eval} />
              </CardTitle>
              <CardDescription className="text-xs">Run evaluation</CardDescription>
              <CardAction>
                  <Button
                    size="sm"
                    className="h-8"
                    onClick={() => runStep("eval", {})}
                    disabled={!projectDir || isBusy}
                  >
                    <Play className="h-3.5 w-3.5 mr-2" /> Run
                  </Button>
                </CardAction>
            </CardHeader>
            <CardContent className="px-4 text-xs text-muted-foreground">
              {detectedCommands?.eval?.command || "python eval.py"}
            </CardContent>
          </Card>

          {/* Report Step */}
          <Card className="py-4">
            <CardHeader className="px-4">
              <CardTitle className="text-sm flex items-center gap-2">
                Report <StatusBadge status={stepStatuses.report} />
              </CardTitle>
              <CardDescription className="text-xs">Generate execution report</CardDescription>
              <CardAction>
                  <Button
                    size="sm"
                    className="h-8"
                    onClick={() => runStep("report", { output_format: "html" })}
                    disabled={!projectDir || isBusy}
                  >
                    <FileText className="h-3.5 w-3.5 mr-2" /> Generate
                  </Button>
                </CardAction>
            </CardHeader>
          </Card>
        </div>
      </ScrollArea>
    </div>
  )
}
