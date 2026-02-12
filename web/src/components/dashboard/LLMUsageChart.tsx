"use client"

import { useMemo } from "react"
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { LLMUsageSummary } from "@/lib/types"

interface LLMUsageChartProps {
  data: LLMUsageSummary
}

const BAR_COLORS = ["#10b981", "#8b5cf6", "#6b7280", "#3b82f6", "#f59e0b"]

function formatProviderLabel(value: string): string {
  if (!value) return "Unknown"
  return value
    .split(/[_-]/g)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ")
}

export function LLMUsageChart({ data }: LLMUsageChartProps) {
  const providerKeys = useMemo(() => {
    const totals = new Map<string, number>()
    for (const row of data.daily || []) {
      for (const [provider, count] of Object.entries(row.providers || {})) {
        totals.set(provider, (totals.get(provider) || 0) + Number(count || 0))
      }
    }
    return [...totals.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
      .map(([name]) => name)
  }, [data.daily])

  const chartRows = useMemo(() => {
    return (data.daily || []).map((row) => {
      const next: Record<string, number | string> = {
        date: row.date,
        total_tokens: row.total_tokens,
      }
      for (const key of providerKeys) {
        next[key] = Number(row.providers?.[key] || 0)
      }
      return next
    })
  }, [data.daily, providerKeys])

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">LLM Token Usage ({data.window_days} Days)</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={chartRows}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" fontSize={12} />
            <YAxis fontSize={12} tickFormatter={(v) => `${Math.round(Number(v) / 1000)}k`} />
            <Tooltip formatter={(value) => `${Number(value).toLocaleString()} tokens`} />
            <Legend formatter={(value) => formatProviderLabel(value)} />
            {providerKeys.map((provider, index) => (
              <Bar
                key={provider}
                dataKey={provider}
                name={provider}
                fill={BAR_COLORS[index % BAR_COLORS.length]}
                stackId="providers"
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
