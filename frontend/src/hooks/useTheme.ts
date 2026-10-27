import { useEffect, useState } from 'react'

// Light/dark mode. Until the user flips Dark mode in the account menu we follow the system setting;
// after that their choice is stored and set as <html data-theme="…">, which index.css reads.
// index.html applies a stored choice before React starts, so the page doesn't flash.

type Theme = 'light' | 'dark'
const KEY = 'theme'
const systemDark = () => window.matchMedia('(prefers-color-scheme: dark)')

function storedTheme(): Theme | null {
  try {
    const theme = localStorage.getItem(KEY)
    return theme === 'light' || theme === 'dark' ? theme : null
  } catch {
    return null // storage blocked (private window, strict settings): just follow the system
  }
}

export function useTheme() {
  const [choice, setChoice] = useState<Theme | null>(storedTheme)
  const [systemIsDark, setSystemIsDark] = useState(() => systemDark().matches)

  // Keep up with the system setting while the user hasn't picked one.
  useEffect(() => {
    const query = systemDark()
    const onChange = (e: MediaQueryListEvent) => setSystemIsDark(e.matches)
    query.addEventListener('change', onChange)
    return () => query.removeEventListener('change', onChange)
  }, [])

  const theme: Theme = choice ?? (systemIsDark ? 'dark' : 'light')

  function toggle() {
    const next: Theme = theme === 'dark' ? 'light' : 'dark'
    setChoice(next)
    document.documentElement.dataset.theme = next
    try {
      localStorage.setItem(KEY, next)
    } catch {
      // Not saved; it still applies until the tab is closed.
    }
  }

  return { theme, toggle }
}
