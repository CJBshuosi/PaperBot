"use client"

import { useEffect, useMemo, useState } from "react"
import { usePanelRef } from "react-resizable-panels"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable"

type PanelKey = "rail" | "list" | "detail"

type SplitPanelsProps = {
  storageKey: string
  rail: React.ReactNode
  list: React.ReactNode
  detail: React.ReactNode
  className?: string
}

const MOBILE_BREAKPOINT = 1024

const DEFAULT_COLLAPSED = {
  rail: false,
  list: false,
  detail: false,
}

const DEFAULT_LAYOUT = {
  rail: 20,
  list: 50,
  detail: 30,
}

export function SplitPanels({ storageKey, rail, list, detail, className }: SplitPanelsProps) {
  const [isMobile, setIsMobile] = useState(false)
  const [mobileActive, setMobileActive] = useState<PanelKey>("list")
  const [collapsed, setCollapsed] = useState(DEFAULT_COLLAPSED)
  const [layout, setLayout] = useState(DEFAULT_LAYOUT)

  const railPanelRef = usePanelRef()
  const listPanelRef = usePanelRef()
  const detailPanelRef = usePanelRef()

  const collapsedKey = useMemo(() => `${storageKey}:collapsed`, [storageKey])
  const layoutKey = useMemo(() => `${storageKey}:layout`, [storageKey])

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(collapsedKey)
      if (!raw) return
      const parsed = JSON.parse(raw) as Partial<typeof DEFAULT_COLLAPSED>
      setCollapsed((prev) => ({
        ...prev,
        rail: !!parsed.rail,
        list: !!parsed.list,
        detail: !!parsed.detail,
      }))
    } catch {
      // Ignore malformed persisted state.
    }
  }, [collapsedKey])

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(layoutKey)
      if (!raw) return
      const parsed = JSON.parse(raw) as Partial<typeof DEFAULT_LAYOUT>
      setLayout({
        rail: Number(parsed.rail) || DEFAULT_LAYOUT.rail,
        list: Number(parsed.list) || DEFAULT_LAYOUT.list,
        detail: Number(parsed.detail) || DEFAULT_LAYOUT.detail,
      })
    } catch {
      // Ignore malformed persisted layout.
    }
  }, [layoutKey])

  useEffect(() => {
    const update = () => setIsMobile(window.innerWidth < MOBILE_BREAKPOINT)
    update()
    window.addEventListener("resize", update)
    return () => window.removeEventListener("resize", update)
  }, [])

  useEffect(() => {
    if (isMobile) return
    if (collapsed.rail) railPanelRef.current?.collapse()
    if (collapsed.list) listPanelRef.current?.collapse()
    if (collapsed.detail) detailPanelRef.current?.collapse()
  }, [collapsed, isMobile, railPanelRef, listPanelRef, detailPanelRef])

  const setCollapsedState = (key: PanelKey, value: boolean) => {
    setCollapsed((prev) => {
      const next = { ...prev, [key]: value }
      try {
        window.localStorage.setItem(collapsedKey, JSON.stringify(next))
      } catch {
        // Ignore storage failures.
      }
      return next
    })
  }

  if (isMobile) {
    return (
      <div className={cn("flex h-full min-h-0 flex-col", className)}>
        <div className="flex gap-1 border-b bg-background/80 p-2">
          <Button size="sm" variant={mobileActive === "rail" ? "secondary" : "ghost"} onClick={() => setMobileActive("rail")}>Rail</Button>
          <Button size="sm" variant={mobileActive === "list" ? "secondary" : "ghost"} onClick={() => setMobileActive("list")}>List</Button>
          <Button size="sm" variant={mobileActive === "detail" ? "secondary" : "ghost"} onClick={() => setMobileActive("detail")}>Detail</Button>
        </div>
        <div className="flex-1 min-h-0 overflow-auto">
          {mobileActive === "rail" && rail}
          {mobileActive === "list" && list}
          {mobileActive === "detail" && detail}
        </div>
      </div>
    )
  }

  return (
    <div className={cn("flex h-full min-h-0 flex-col", className)}>
      <div className="flex items-center gap-1 border-b bg-background/80 p-2">
        <Button size="sm" variant={collapsed.rail ? "outline" : "secondary"} onClick={() => (collapsed.rail ? railPanelRef.current?.expand() : railPanelRef.current?.collapse())}>
          Rail
        </Button>
        <Button size="sm" variant={collapsed.list ? "outline" : "secondary"} onClick={() => (collapsed.list ? listPanelRef.current?.expand() : listPanelRef.current?.collapse())}>
          List
        </Button>
        <Button size="sm" variant={collapsed.detail ? "outline" : "secondary"} onClick={() => (collapsed.detail ? detailPanelRef.current?.expand() : detailPanelRef.current?.collapse())}>
          Detail
        </Button>
      </div>
      <ResizablePanelGroup
        orientation="horizontal"
        defaultLayout={layout}
        onLayoutChange={(next) => {
          const normalized = {
            rail: Number(next.rail || DEFAULT_LAYOUT.rail),
            list: Number(next.list || DEFAULT_LAYOUT.list),
            detail: Number(next.detail || DEFAULT_LAYOUT.detail),
          }
          setLayout(normalized)
          try {
            window.localStorage.setItem(layoutKey, JSON.stringify(normalized))
          } catch {
            // Ignore storage failures.
          }
        }}
        className="flex-1 min-h-0"
      >
        <ResizablePanel
          id="rail"
          panelRef={railPanelRef}
          defaultSize={20}
          minSize={12}
          collapsible
          collapsedSize={0}
          onResize={({ inPixels }) => setCollapsedState("rail", inPixels < 2)}
          className="min-h-0 overflow-auto"
        >
          {rail}
        </ResizablePanel>

        <ResizableHandle withHandle />

        <ResizablePanel
          id="list"
          panelRef={listPanelRef}
          defaultSize={50}
          minSize={24}
          collapsible
          collapsedSize={0}
          onResize={({ inPixels }) => setCollapsedState("list", inPixels < 2)}
          className="min-h-0 overflow-auto"
        >
          {list}
        </ResizablePanel>

        <ResizableHandle withHandle />

        <ResizablePanel
          id="detail"
          panelRef={detailPanelRef}
          defaultSize={30}
          minSize={18}
          collapsible
          collapsedSize={0}
          onResize={({ inPixels }) => setCollapsedState("detail", inPixels < 2)}
          className="min-h-0 overflow-auto"
        >
          {detail}
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  )
}
