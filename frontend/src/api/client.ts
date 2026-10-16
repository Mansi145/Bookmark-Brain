// Base URL of the FastAPI backend. Set VITE_API_URL in .env.local (dev) or on Vercel (prod).
export const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export async function apiGet<T>(path: string): Promise<T> {
  // credentials: 'include' sends the session cookie once auth exists (Phase 1).
  const res = await fetch(`${API_URL}${path}`, { credentials: 'include' })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json() as Promise<T>
}
