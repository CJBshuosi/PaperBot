"use client"

import { useEffect, useMemo, useState } from "react"
import { Loader2, Plus, Save, Trash2, Wrench } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"

type ModelEndpoint = {
  id: number
  name: string
  vendor: string
  base_url?: string | null
  api_key_env: string
  models: string[]
  task_types: string[]
  enabled: boolean
  is_default: boolean
  api_key_present?: boolean
}

type ModelEndpointListResponse = {
  items: ModelEndpoint[]
}

type FormState = {
  id?: number
  name: string
  vendor: string
  base_url: string
  api_key_env: string
  models: string
  task_types: string
  enabled: boolean
  is_default: boolean
}

const EMPTY_FORM: FormState = {
  name: "",
  vendor: "openai_compatible",
  base_url: "",
  api_key_env: "OPENAI_API_KEY",
  models: "",
  task_types: "",
  enabled: true,
  is_default: false,
}

function toPayload(form: FormState) {
  return {
    name: form.name.trim(),
    vendor: form.vendor,
    base_url: form.base_url.trim() || null,
    api_key_env: form.api_key_env.trim(),
    models: form.models.split(",").map((x) => x.trim()).filter(Boolean),
    task_types: form.task_types.split(",").map((x) => x.trim()).filter(Boolean),
    enabled: form.enabled,
    is_default: form.is_default,
  }
}

export default function SettingsPage() {
  const [items, setItems] = useState<ModelEndpoint[]>([])
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [testingId, setTestingId] = useState<number | null>(null)
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  const editing = useMemo(() => typeof form.id === "number", [form.id])

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch("/api/model-endpoints")
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
      const payload = (await res.json()) as ModelEndpointListResponse
      setItems(payload.items || [])
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setItems([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load().catch(() => {})
  }, [])

  function resetForm() {
    setForm(EMPTY_FORM)
    setMessage(null)
    setError(null)
  }

  function editItem(item: ModelEndpoint) {
    setForm({
      id: item.id,
      name: item.name,
      vendor: item.vendor,
      base_url: item.base_url || "",
      api_key_env: item.api_key_env,
      models: (item.models || []).join(", "),
      task_types: (item.task_types || []).join(", "),
      enabled: item.enabled,
      is_default: item.is_default,
    })
    setMessage(null)
    setError(null)
  }

  async function saveItem() {
    setSaving(true)
    setError(null)
    setMessage(null)
    try {
      const payload = toPayload(form)
      if (!payload.name) throw new Error("Name is required")
      if (!payload.models.length) throw new Error("At least one model is required")

      const res = await fetch(editing ? `/api/model-endpoints/${form.id}` : "/api/model-endpoints", {
        method: editing ? "PATCH" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
      if (!res.ok) {
        const text = await res.text().catch(() => "")
        throw new Error(text || `${res.status} ${res.statusText}`)
      }
      await load()
      resetForm()
      setMessage(editing ? "Provider updated." : "Provider created.")
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setSaving(false)
    }
  }

  async function deleteItem(id: number) {
    if (!confirm("Delete this provider?")) return
    setError(null)
    setMessage(null)
    try {
      const res = await fetch(`/api/model-endpoints/${id}`, { method: "DELETE" })
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
      await load()
      if (form.id === id) {
        resetForm()
      }
      setMessage("Provider removed.")
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  async function testItem(id: number) {
    setTestingId(id)
    setError(null)
    setMessage(null)
    try {
      const res = await fetch(`/api/model-endpoints/${id}/test`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ remote: false }),
      })
      const payload = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(String(payload?.detail || `${res.status} ${res.statusText}`))
      }
      setMessage(payload?.message || "Connection test passed.")
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setTestingId(null)
    }
  }

  return (
    <div className="flex-1 space-y-4 p-8 pt-6">
      <h2 className="text-3xl font-bold tracking-tight">Settings</h2>

      <Card>
        <CardHeader>
          <CardTitle>Model Providers</CardTitle>
          <CardDescription>
            Add OpenAI-compatible or native vendors, set default provider, and route tasks by model.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {error && <p className="text-sm text-destructive">{error}</p>}
          {message && <p className="text-sm text-green-600">{message}</p>}

          <div className="grid gap-3 md:grid-cols-2">
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Name</label>
              <Input value={form.name} onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))} placeholder="OpenRouter" />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Vendor</label>
              <select
                value={form.vendor}
                onChange={(e) => setForm((p) => ({ ...p, vendor: e.target.value }))}
                className="h-9 rounded-md border bg-background px-3 text-sm w-full"
              >
                <option value="openai_compatible">OpenAI Compatible</option>
                <option value="openai">OpenAI</option>
                <option value="anthropic">Anthropic</option>
                <option value="ollama">Ollama</option>
              </select>
            </div>

            <div className="space-y-1.5 md:col-span-2">
              <label className="text-sm font-medium">Base URL</label>
              <Input value={form.base_url} onChange={(e) => setForm((p) => ({ ...p, base_url: e.target.value }))} placeholder="https://openrouter.ai/api/v1" />
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-medium">API Key Env</label>
              <Input value={form.api_key_env} onChange={(e) => setForm((p) => ({ ...p, api_key_env: e.target.value }))} placeholder="OPENAI_API_KEY" />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Models (comma separated)</label>
              <Input value={form.models} onChange={(e) => setForm((p) => ({ ...p, models: e.target.value }))} placeholder="gpt-4o-mini, gpt-4o" />
            </div>

            <div className="space-y-1.5 md:col-span-2">
              <label className="text-sm font-medium">Task Routing (comma separated)</label>
              <Input
                value={form.task_types}
                onChange={(e) => setForm((p) => ({ ...p, task_types: e.target.value }))}
                placeholder="default, summary, reasoning, code"
              />
            </div>

            <div className="flex items-center gap-2">
              <input
                id="endpoint-enabled"
                type="checkbox"
                checked={form.enabled}
                onChange={(e) => setForm((p) => ({ ...p, enabled: e.target.checked }))}
              />
              <label htmlFor="endpoint-enabled" className="text-sm">Enabled</label>
            </div>
            <div className="flex items-center gap-2">
              <input
                id="endpoint-default"
                type="checkbox"
                checked={form.is_default}
                onChange={(e) => setForm((p) => ({ ...p, is_default: e.target.checked }))}
              />
              <label htmlFor="endpoint-default" className="text-sm">Default Provider</label>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button onClick={saveItem} disabled={saving}>
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
              {editing ? "Update" : "Create"}
            </Button>
            <Button variant="outline" onClick={resetForm} disabled={saving}>Reset</Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Configured Providers</CardTitle>
          <CardDescription>Used by LLM service router for task-level model selection.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {loading ? (
            <p className="text-sm text-muted-foreground">Loading providers...</p>
          ) : !items.length ? (
            <p className="text-sm text-muted-foreground">No providers yet.</p>
          ) : (
            items.map((item) => (
              <div key={item.id} className="rounded-md border p-3 flex flex-col gap-2">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium text-sm">{item.name}</span>
                    <Badge variant="outline" className="text-xs">{item.vendor}</Badge>
                    {item.is_default && <Badge className="text-xs">default</Badge>}
                    {!item.enabled && <Badge variant="secondary" className="text-xs">disabled</Badge>}
                    <Badge variant={item.api_key_present ? "secondary" : "destructive"} className="text-xs">
                      {item.api_key_present ? "key detected" : "missing key"}
                    </Badge>
                  </div>

                  <div className="flex items-center gap-1.5">
                    <Button size="sm" variant="outline" onClick={() => editItem(item)}>
                      <Plus className="h-3.5 w-3.5" />
                      Edit
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => testItem(item.id)}
                      disabled={testingId === item.id}
                    >
                      {testingId === item.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Wrench className="h-3.5 w-3.5" />}
                      Test
                    </Button>
                    <Button size="sm" variant="destructive" onClick={() => deleteItem(item.id)}>
                      <Trash2 className="h-3.5 w-3.5" />
                      Delete
                    </Button>
                  </div>
                </div>

                <div className="text-xs text-muted-foreground">
                  <div>base_url: {item.base_url || "(default)"}</div>
                  <div>api_key_env: {item.api_key_env}</div>
                  <div>models: {(item.models || []).join(", ") || "-"}</div>
                  <div>task_routes: {(item.task_types || []).join(", ") || "-"}</div>
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  )
}
