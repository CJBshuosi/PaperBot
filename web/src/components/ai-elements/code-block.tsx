"use client"

import { useState } from "react"
import { Check, Copy } from "lucide-react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

interface CodeBlockProps {
  code: string
  title?: string
  language?: string
  className?: string
}

export function CodeBlock({ code, title = "Code", language, className }: CodeBlockProps) {
  const [copied, setCopied] = useState(false)

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(code)
      setCopied(true)
      setTimeout(() => setCopied(false), 1200)
    } catch {
      setCopied(false)
    }
  }

  return (
    <div className={cn("rounded-md border bg-muted/20", className)}>
      <div className="flex items-center justify-between gap-2 border-b px-2 py-1.5">
        <div className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
          {title}
          {language ? ` · ${language}` : ""}
        </div>
        <Button
          type="button"
          size="sm"
          variant="ghost"
          className="h-6 gap-1 px-2 text-[11px]"
          onClick={copy}
          aria-label="Copy code block"
        >
          {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
          {copied ? "Copied" : "Copy"}
        </Button>
      </div>
      <pre className="max-h-56 overflow-auto p-2 text-xs">
        <code className="font-mono whitespace-pre-wrap break-all">{code}</code>
      </pre>
    </div>
  )
}
