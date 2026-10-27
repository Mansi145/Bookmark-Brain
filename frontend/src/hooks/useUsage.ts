import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import type { Usage } from '../api/types'

/** Today's AI summaries (shared cache: the feed rows, the detail panel and Settings). */
export function useUsage() {
  const usage = useQuery({ queryKey: ['usage'], queryFn: () => api.get<Usage>('/api/usage') })
  const limitReached = Boolean(usage.data && usage.data.summaries_used >= usage.data.summaries_limit)
  return { ...usage, limitReached }
}
