// Base URL of the FastAPI backend. Set VITE_API_URL in .env.local (dev) or on Vercel (prod).
export const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

/**
 * Fires when a request comes back 401 while we thought we were signed in (the session cookie
 * expired or was revoked), so the app can show "You've been signed out". /api/me and sign-in
 * itself are left out: a 401 there just means "not signed in".
 */
export const sessionEnded = new EventTarget()

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method,
    // Sends our httpOnly session cookie along with the request.
    credentials: 'include',
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!res.ok) {
    if (res.status === 401 && path !== '/api/me' && !path.startsWith('/api/auth/')) {
      sessionEnded.dispatchEvent(new Event('ended'))
    }
    const detail = await res
      .json()
      .then((data) => data.detail)
      .catch(() => res.statusText)
    throw new ApiError(res.status, typeof detail === 'string' ? detail : res.statusText)
  }
  return (res.status === 204 ? undefined : await res.json()) as T
}

export const api = {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T>(path: string, body?: unknown) => request<T>('POST', path, body ?? {}),
  patch: <T>(path: string, body: unknown) => request<T>('PATCH', path, body),
  delete: <T>(path: string, body?: unknown) => request<T>('DELETE', path, body),
}
