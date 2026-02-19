"use client"

import { useEffect, useMemo, useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { useStudioStore } from "@/lib/store/studio-store"
import { useProjectContext } from "@/lib/store/project-context"
import { cn } from "@/lib/utils"
import { FileText, Folder, FolderOpen, RefreshCw, Search, ChevronRight, ChevronDown } from "lucide-react"

type FileIndexResponse = {
    project_dir: string
    files: string[]
    directories?: string[]
    truncated?: boolean
}

function languageForPath(path: string): string {
    const lower = path.toLowerCase()
    if (lower.endsWith(".py")) return "python"
    if (lower.endsWith(".ts") || lower.endsWith(".tsx")) return "typescript"
    if (lower.endsWith(".js") || lower.endsWith(".jsx")) return "javascript"
    if (lower.endsWith(".json")) return "json"
    if (lower.endsWith(".yaml") || lower.endsWith(".yml")) return "yaml"
    if (lower.endsWith(".md")) return "markdown"
    if (lower.endsWith(".toml")) return "toml"
    if (lower.endsWith(".txt")) return "plaintext"
    if (lower.endsWith(".sh")) return "shell"
    return "plaintext"
}

interface FileTreeNode {
    name: string
    path: string
    isDirectory: boolean
    children: FileTreeNode[]
}

function buildFileTree(files: string[]): FileTreeNode[] {
    const root: FileTreeNode[] = []
    const nodeMap = new Map<string, FileTreeNode>()

    for (const filePath of files) {
        const parts = filePath.split('/')
        let currentPath = ''
        let currentLevel = root

        for (let i = 0; i < parts.length; i++) {
            const part = parts[i]
            const isLast = i === parts.length - 1
            currentPath = currentPath ? `${currentPath}/${part}` : part

            let node = nodeMap.get(currentPath)
            if (!node) {
                node = {
                    name: part,
                    path: currentPath,
                    isDirectory: !isLast,
                    children: [],
                }
                nodeMap.set(currentPath, node)
                currentLevel.push(node)
            }
            currentLevel = node.children
        }
    }

    const sortNodes = (nodes: FileTreeNode[]) => {
        nodes.sort((a, b) => {
            if (a.isDirectory !== b.isDirectory) return a.isDirectory ? -1 : 1
            return a.name.localeCompare(b.name)
        })
        nodes.forEach(n => sortNodes(n.children))
    }
    sortNodes(root)
    return root
}

interface FileTreeItemProps {
    node: FileTreeNode
    depth: number
    activeFile: string | null
    expandedDirs: Set<string>
    onToggleDir: (path: string) => void
    onSelectFile: (path: string) => void
}

function FileTreeItem({ node, depth, activeFile, expandedDirs, onToggleDir, onSelectFile }: FileTreeItemProps) {
    const isExpanded = expandedDirs.has(node.path)
    const isActive = activeFile === node.path

    if (node.isDirectory) {
        return (
            <div>
                <button
                    onClick={() => onToggleDir(node.path)}
                    className="w-full flex items-center gap-1.5 px-2 py-1.5 text-sm hover:bg-muted/50 transition-colors rounded"
                    style={{ paddingLeft: `${depth * 16 + 8}px` }}
                >
                    {isExpanded ? (
                        <ChevronDown className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                    ) : (
                        <ChevronRight className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                    )}
                    {isExpanded ? (
                        <FolderOpen className="h-4 w-4 text-amber-500 shrink-0" />
                    ) : (
                        <Folder className="h-4 w-4 text-amber-500 shrink-0" />
                    )}
                    <span className="truncate">{node.name}</span>
                </button>
                {isExpanded && node.children.map(child => (
                    <FileTreeItem
                        key={child.path}
                        node={child}
                        depth={depth + 1}
                        activeFile={activeFile}
                        expandedDirs={expandedDirs}
                        onToggleDir={onToggleDir}
                        onSelectFile={onSelectFile}
                    />
                ))}
            </div>
        )
    }

    return (
        <button
            onClick={() => onSelectFile(node.path)}
            className={cn(
                "w-full flex items-center gap-1.5 px-2 py-1.5 text-sm hover:bg-muted/50 transition-colors rounded",
                isActive && "bg-primary/10 text-primary"
            )}
            style={{ paddingLeft: `${depth * 16 + 8}px` }}
            title={node.path}
        >
            <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
            <span className="truncate">{node.name}</span>
        </button>
    )
}

export function FilesPanel() {
    const { papers, selectedPaperId, lastGenCodeResult } = useStudioStore()
    const selectedPaper = useMemo(() =>
        selectedPaperId ? papers.find(p => p.id === selectedPaperId) ?? null : null,
        [papers, selectedPaperId]
    )

    const projectDir = selectedPaper?.outputDir || lastGenCodeResult?.outputDir || ""
    const { files, activeFile, addFile, setActiveFile } = useProjectContext()
    const openFiles = useMemo(() => Object.values(files), [files])

    const [fileIndex, setFileIndex] = useState<string[]>([])
    const [loadingIndex, setLoadingIndex] = useState(false)
    const [query, setQuery] = useState("")
    const [expandedDirs, setExpandedDirs] = useState<Set<string>>(new Set())


    const filteredFiles = useMemo(() => {
        const q = query.trim().toLowerCase()
        if (!q) return fileIndex
        return fileIndex.filter((p) => p.toLowerCase().includes(q))
    }, [fileIndex, query])

    const fileTree = useMemo(() => buildFileTree(filteredFiles), [filteredFiles])

    const refreshIndex = async () => {
        if (!projectDir) return
        setLoadingIndex(true)
        try {
            const res = await fetch(`/api/runbook/files?project_dir=${encodeURIComponent(projectDir)}&recursive=true`)
            if (!res.ok) return
            const data = (await res.json()) as FileIndexResponse
            setFileIndex(data.files || [])
            const firstLevelDirs = new Set<string>()
            for (const f of data.files || []) {
                const firstPart = f.split('/')[0]
                if (f.includes('/')) firstLevelDirs.add(firstPart)
            }
            setExpandedDirs(firstLevelDirs)
        } catch {
            setFileIndex([])
        } finally {
            setLoadingIndex(false)
        }
    }

    useEffect(() => {
        setFileIndex([])
        setQuery("")
        setExpandedDirs(new Set())
        if (projectDir) refreshIndex()
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [projectDir])

    const openFile = async (path: string) => {
        if (!projectDir) return
        try {
            const res = await fetch(`/api/runbook/file?project_dir=${encodeURIComponent(projectDir)}&path=${encodeURIComponent(path)}`)
            if (!res.ok) return
            const data = (await res.json()) as { path: string; content: string }
            addFile(data.path, data.content, languageForPath(data.path))
        } catch {
            // ignore
        }
    }

    const toggleDir = (path: string) => {
        setExpandedDirs(prev => {
            const next = new Set(prev)
            if (next.has(path)) next.delete(path)
            else next.add(path)
            return next
        })
    }

    return (
        <div className="h-full min-w-0 min-h-0 bg-muted/30 dark:bg-zinc-900/50 flex flex-col overflow-hidden border-l">
            {/* Header */}
            <div className="px-4 h-12 flex items-center justify-between shrink-0">
                <span className="text-sm font-semibold">Files</span>
                <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={refreshIndex}
                    disabled={!projectDir || loadingIndex}
                >
                    <RefreshCw className={cn("h-4 w-4", loadingIndex && "animate-spin")} />
                </Button>
            </div>

            {/* Search */}
            <div className="px-3 pb-2">
                <div className="relative">
                    <Search className="absolute left-2.5 top-2 h-4 w-4 text-muted-foreground" />
                    <Input
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Filter files..."
                        className="pl-8 h-8 bg-background/60 border-0 focus-visible:ring-1"
                        disabled={!projectDir}
                    />
                </div>
            </div>

            {/* File Tree or Open Files */}
            <ScrollArea className="flex-1 min-h-0">
                <div className="px-2 pb-4">
                    {projectDir ? (
                        /* Show file tree when project directory exists */
                        fileTree.length === 0 ? (
                            <div className="text-sm text-muted-foreground text-center py-8">
                                {loadingIndex ? "Loading..." : "No files"}
                            </div>
                        ) : (
                            fileTree.map(node => (
                                <FileTreeItem
                                    key={node.path}
                                    node={node}
                                    depth={0}
                                    activeFile={activeFile}
                                    expandedDirs={expandedDirs}
                                    onToggleDir={toggleDir}
                                    onSelectFile={openFile}
                                />
                            ))
                        )
                    ) : openFiles.length > 0 ? (
                        /* Show open files when no project directory */
                        openFiles.map((file) => (
                            <button
                                key={file.name}
                                className={cn(
                                    "w-full flex items-center gap-1.5 px-2 py-1.5 text-sm hover:bg-muted/50 transition-colors rounded",
                                    activeFile === file.name && "bg-primary/10 text-primary"
                                )}
                                onClick={() => setActiveFile(file.name)}
                            >
                                <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
                                <span className="truncate">{file.name.split('/').pop()}</span>
                            </button>
                        ))
                    ) : (
                        <div className="flex flex-col items-center justify-center text-muted-foreground py-12 px-4 text-center">
                            <Folder className="h-10 w-10 mb-3 opacity-20" />
                            <p className="text-sm">Run Paper2Code to generate files</p>
                        </div>
                    )}
                </div>
            </ScrollArea>
        </div>
    )
}
