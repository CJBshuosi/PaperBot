import { Suspense } from "react"

import ResearchSplitWorkspace from "@/components/research/ResearchSplitWorkspace"

export default function ResearchPage() {
  return (
    <div className="flex-1 bg-stone-50/50 dark:bg-background">
      <Suspense fallback={<div className="p-4 text-sm text-muted-foreground">Loading research workspace...</div>}>
        <ResearchSplitWorkspace />
      </Suspense>
    </div>
  )
}
