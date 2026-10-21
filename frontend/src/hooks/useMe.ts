import { useQuery } from '@tanstack/react-query'
import { api, ApiError } from '../api/client'
import type { User } from '../api/types'

/** The signed-in user, or null when signed out (401). */
export function useMe() {
  return useQuery({
    queryKey: ['me'],
    queryFn: async () => {
      try {
        return await api.get<User>('/api/me')
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) return null
        throw err
      }
    },
    staleTime: 5 * 60 * 1000,
    retry: false,
  })
}
