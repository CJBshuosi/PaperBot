import { Suspense } from "react"

import ResearchDiscoveryPage from "@/components/research/ResearchDiscoveryPage"

export default function ResearchDiscoveryRoutePage() {
  return (
    <div className="flex-1 bg-stone-50/50 dark:bg-background">
      <Suspense fallback={<div className="p-4 text-sm text-muted-foreground">Loading discovery workspace...</div>}>
        <ResearchDiscoveryPage />
      </Suspense>
    </div>
  )
}
