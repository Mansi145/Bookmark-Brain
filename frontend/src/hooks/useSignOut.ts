import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'

/** Sign out (account menu and Settings → Account): clear the session cookie and every cached query. */
export function useSignOut() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => api.post('/api/auth/logout'),
    onSuccess: () => {
      queryClient.clear()
      queryClient.setQueryData(['me'], null)
    },
  })
}
