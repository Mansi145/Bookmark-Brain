import { useMutation } from '@tanstack/react-query'
import { api, ApiError } from '../api/client'
import { RowButton } from './RowButton'

// Local testing only (not a designed screen): the layout mounts this only in `npm run dev`, so
// production builds don't contain it, and the backend answers 404 unless DEV_TOOLS=true.
// It lets you try the Limit reached dialog without making 50 real summaries.

export default function DevTools() {
  const action = useMutation({
    mutationFn: (what: 'use-up' | 'reset') => api.post<void>(`/api/usage/dev/${what}`),
  })

  const status = action.isError
    ? action.error instanceof ApiError && action.error.status === 404
      ? 'Off: add DEV_TOOLS=true to backend/.env and restart the backend.'
      : `Failed: ${action.error.message}`
    : action.isSuccess
      ? action.variables === 'use-up'
        ? 'Used up. Press any Summarise to see the dialog.'
        : 'Reset: a full allowance again, and the email can be sent again.'
      : null

  return (
    <aside
      aria-label="Dev tools"
      className="fixed bottom-4 left-4 z-20 flex max-w-[300px] flex-col gap-2 rounded-xl border border-dashed border-line bg-panel p-3 text-[13px] text-ink2 shadow-[0_8px_24px_rgba(0,0,0,0.18)]"
    >
      <span className="font-semibold text-ink">Dev tools · daily AI limit</span>
      <div className="flex flex-wrap gap-2">
        <RowButton compact onClick={() => action.mutate('use-up')} disabled={action.isPending}>
          Use up today's limit
        </RowButton>
        <RowButton compact onClick={() => action.mutate('reset')} disabled={action.isPending}>
          Reset
        </RowButton>
      </div>
      {status && <span role="status">{status}</span>}
    </aside>
  )
}
