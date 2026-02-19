import TopicWorkflowDashboard from "@/components/research/TopicWorkflowDashboard"

type WorkflowsPageProps = {
  searchParams?: Promise<Record<string, string | string[] | undefined>>
}

export default async function WorkflowsPage({ searchParams }: WorkflowsPageProps) {
  const params = searchParams ? await searchParams : {}
  const rawQuery = params?.query
  const queryValue = Array.isArray(rawQuery) ? rawQuery[0] : rawQuery
  const initialQueries = queryValue
    ? queryValue
        .split(",")
        .map((q) => q.trim())
        .filter(Boolean)
    : undefined

  return (
    <div className="flex-1 space-y-4 p-8 pt-6">
      <TopicWorkflowDashboard initialQueries={initialQueries} />
    </div>
  )
}
