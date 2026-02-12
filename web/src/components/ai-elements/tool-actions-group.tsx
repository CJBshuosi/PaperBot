"use client"

import { ReactNode } from "react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

type ToolAction = {
  id: string
  label: string
  icon?: ReactNode
  onClick?: () => void
  disabled?: boolean
  variant?: "default" | "outline" | "ghost" | "destructive" | "secondary"
  className?: string
}

interface ToolActionsGroupProps {
  actions: ToolAction[]
  className?: string
  ariaLabel?: string
}

export function ToolActionsGroup({
  actions,
  className,
  ariaLabel = "Tool actions",
}: ToolActionsGroupProps) {
  if (!actions.length) return null

  return (
    <div className={cn("flex flex-wrap items-center gap-2", className)} role="group" aria-label={ariaLabel}>
      {actions.map((action) => (
        <Button
          key={action.id}
          size="sm"
          variant={action.variant ?? "outline"}
          className={cn("h-8 gap-1.5", action.className)}
          onClick={action.onClick}
          disabled={action.disabled}
        >
          {action.icon}
          {action.label}
        </Button>
      ))}
    </div>
  )
}
