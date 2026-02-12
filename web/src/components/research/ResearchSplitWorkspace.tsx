"use client"

import Link from "next/link"
import { BookOpen, Library, LayoutPanelLeft, SearchCheck, Settings2 } from "lucide-react"

import { SplitPanels } from "@/components/layout/SplitPanels"
import ResearchPageNew from "@/components/research/ResearchPageNew"
import SavedPapersList from "@/components/research/SavedPapersList"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

function RailPanel() {
  return (
    <div className="p-3 space-y-3">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <LayoutPanelLeft className="h-4 w-4" /> Research Rail
          </CardTitle>
          <CardDescription>Track-scoped shortcuts and workspace entry points.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          <Badge variant="secondary" className="mr-1">Search</Badge>
          <Badge variant="secondary" className="mr-1">Feed</Badge>
          <Badge variant="secondary">Memory</Badge>
          <div className="grid gap-1 pt-2">
            <Button asChild size="sm" variant="outline" className="justify-start">
              <Link href="/dashboard">
                <SearchCheck className="mr-2 h-3.5 w-3.5" />
                Dashboard
              </Link>
            </Button>
            <Button asChild size="sm" variant="outline" className="justify-start">
              <Link href="/papers">
                <Library className="mr-2 h-3.5 w-3.5" />
                Papers Library
              </Link>
            </Button>
            <Button asChild size="sm" variant="outline" className="justify-start">
              <Link href="/settings">
                <Settings2 className="mr-2 h-3.5 w-3.5" />
                Model Providers
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function DetailPanel() {
  return (
    <div className="p-3 space-y-3">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <BookOpen className="h-4 w-4" /> Saved Snapshot
          </CardTitle>
          <CardDescription>Live view from papers library for quick context.</CardDescription>
        </CardHeader>
      </Card>
      <SavedPapersList />
    </div>
  )
}

export default function ResearchSplitWorkspace() {
  return (
    <SplitPanels
      storageKey="paperbot.research.split.v1"
      rail={<RailPanel />}
      list={<ResearchPageNew />}
      detail={<DetailPanel />}
      className="h-[calc(100vh-4rem)]"
    />
  )
}
