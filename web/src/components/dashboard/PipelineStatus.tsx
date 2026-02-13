"use client"

import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { AlertCircle, CheckCircle2, Loader2, Database } from "lucide-react"
import type { PipelineTask } from "@/lib/types"

interface PipelineStatusProps {
    tasks: PipelineTask[]
}

const statusIcons: Record<string, React.ReactNode> = {
    downloading: <Loader2 className="h-3 w-3 animate-spin text-blue-500" />,
    analyzing: <Loader2 className="h-3 w-3 animate-spin text-yellow-500" />,
    building: <Loader2 className="h-3 w-3 animate-spin text-orange-500" />,
    testing: <Loader2 className="h-3 w-3 animate-spin text-purple-500" />,
    success: <CheckCircle2 className="h-3 w-3 text-green-500" />,
    failed: <AlertCircle className="h-3 w-3 text-red-500" />,
}

export function PipelineStatus({ tasks }: PipelineStatusProps) {
    return (
        <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 p-3 pb-2">
                <CardTitle className="text-xs font-medium flex items-center gap-1.5">
                    <Database className="h-3 w-3" /> Harvest Runs
                </CardTitle>
                {tasks.length > 0 && (
                    <Badge variant="outline" className="text-[10px] px-1.5 py-0">{tasks.length}</Badge>
                )}
            </CardHeader>
            <CardContent className="p-3 pt-0 space-y-2">
                {tasks.length === 0 ? (
                    <p className="text-xs text-muted-foreground">No harvest runs yet.</p>
                ) : (
                    tasks.map((task) => (
                        <div key={task.id} className="space-y-1">
                            <div className="flex items-center justify-between text-xs">
                                <div className="flex items-center gap-1.5">
                                    {statusIcons[task.status] || statusIcons.building}
                                    <span className="font-medium truncate max-w-[160px]">{task.paper_title}</span>
                                </div>
                                <span className="text-muted-foreground text-[10px]">{task.started_at}</span>
                            </div>
                            <Progress value={task.progress} className="h-1" />
                        </div>
                    ))
                )}
            </CardContent>
        </Card>
    )
}
