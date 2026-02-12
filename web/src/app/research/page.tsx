import { Suspense } from "react"

import ResearchPageNew from "@/components/research/ResearchPageNew"

export default function ResearchPage() {
  return (
    <div className="flex-1 bg-stone-50/50 dark:bg-background">
      <Suspense fallback={<div className="p-4 text-sm text-muted-foreground">Loading research workspace...</div>}>
        <ResearchPageNew />
      </Suspense>
    </div>
  )
}
