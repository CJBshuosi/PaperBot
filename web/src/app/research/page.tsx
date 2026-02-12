import { Suspense } from "react"

import ResearchPageNew from "@/components/research/ResearchPageNew"

export default function ResearchPage() {
  return (
    <div className="flex-1 bg-stone-50/50 dark:bg-background">
      <Suspense fallback={<div className="p-6 text-sm text-muted-foreground">Loading research...</div>}>
        <ResearchPageNew />
      </Suspense>
    </div>
  )
}
