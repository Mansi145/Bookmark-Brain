import { createContext, useContext, useState } from 'react'

// Select mode's state (components/SelectMode.tsx): whether it's on and which stories are picked.
// The feed page holds it; each story's checkbox reads it through the context.

type Selection = { selecting: boolean; selected: Set<number>; toggle: (id: number) => void }

const SelectionContext = createContext<Selection>({ selecting: false, selected: new Set(), toggle: () => {} })

export const SelectionProvider = SelectionContext.Provider
export const useSelection = () => useContext(SelectionContext)

/** Holds Select mode's state for the feed page. */
export function useSelectMode() {
  const [selecting, setSelecting] = useState(false)
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const toggle = (id: number) =>
    setSelected((old) => {
      const next = new Set(old)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  const stop = () => {
    setSelecting(false)
    setSelected(new Set())
  }
  return { selecting, selected, toggle, start: () => setSelecting(true), stop }
}
