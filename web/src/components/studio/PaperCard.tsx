"use client"

import { StudioPaper, StudioPaperStatus } from "@/lib/store/studio-store"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { FileText, Trash2, MoreHorizontal, Play, CheckCircle2, AlertCircle, Loader2, Clock } from "lucide-react"
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

const statusConfig: Record<StudioPaperStatus, {
    label: string
    className: string
    icon: React.ElementType
}> = {
    draft: {
        label: "Draft",
        className: "bg-muted text-muted-foreground",
        icon: FileText,
    },
    generating: {
        label: "Generating",
        className: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
        icon: Loader2,
    },
    ready: {
        label: "Ready",
        className: "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300",
        icon: CheckCircle2,
    },
    running: {
        label: "Running",
        className: "bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300",
        icon: Play,
    },
    completed: {
        label: "Complete",
        className: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300",
        icon: CheckCircle2,
    },
    error: {
        label: "Error",
        className: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300",
        icon: AlertCircle,
    },
}

function formatRelativeTime(dateStr: string): string {
    const date = new Date(dateStr)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const seconds = Math.floor(diff / 1000)
    const minutes = Math.floor(seconds / 60)
    const hours = Math.floor(minutes / 60)
    const days = Math.floor(hours / 24)

    if (seconds < 60) return 'Just now'
    if (minutes < 60) return `${minutes}m ago`
    if (hours < 24) return `${hours}h ago`
    if (days < 7) return `${days}d ago`
    return date.toLocaleDateString()
}

interface PaperCardProps {
    paper: StudioPaper
    isSelected: boolean
    onSelect: () => void
    onDelete: () => void
}

export function PaperCard({ paper, isSelected, onSelect, onDelete }: PaperCardProps) {
    const config = statusConfig[paper.status]
    const StatusIcon = config.icon

    return (
        <div
            onClick={onSelect}
            className={cn(
                "group relative w-full flex flex-col gap-1.5 p-3 rounded-lg text-left transition-all cursor-pointer",
                "hover:bg-muted/50 border border-transparent",
                isSelected && "bg-muted border-border ring-1 ring-border"
            )}
        >
            {/* Title */}
            <div className="flex items-start gap-2">
                <FileText className="h-4 w-4 text-muted-foreground shrink-0 mt-0.5" />
                <p className={cn(
                    "text-sm font-medium line-clamp-2 leading-tight flex-1",
                    isSelected ? "text-foreground" : "text-foreground/80"
                )}>
                    {paper.title || "Untitled Paper"}
                </p>
            </div>

            {/* Status + Time */}
            <div className="flex items-center justify-between gap-2 pl-6">
                <Badge variant="secondary" className={cn("text-[10px] h-5", config.className)}>
                    <StatusIcon className={cn("h-3 w-3 mr-1", paper.status === 'generating' && "animate-spin")} />
                    {config.label}
                </Badge>
                <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                    <Clock className="h-2.5 w-2.5" />
                    {formatRelativeTime(paper.updatedAt)}
                </span>
            </div>

            {/* Actions menu */}
            <div className={cn(
                "absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity",
                isSelected && "opacity-100"
            )}>
                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7"
                            onClick={(e) => e.stopPropagation()}
                        >
                            <MoreHorizontal className="h-4 w-4" />
                        </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                        <DropdownMenuItem
                            className="text-destructive focus:text-destructive"
                            onClick={(e) => {
                                e.stopPropagation()
                                onDelete()
                            }}
                        >
                            <Trash2 className="h-4 w-4 mr-2" />
                            Delete
                        </DropdownMenuItem>
                    </DropdownMenuContent>
                </DropdownMenu>
            </div>
        </div>
    )
}
