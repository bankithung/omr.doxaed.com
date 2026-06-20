import { createContext, useContext, useEffect, useState } from "react"

// Lets a page declare its sub-sections so the AppShell can render them as a
// SECOND sidebar column (the "sub-bar") next to the always-on org/class sidebar
// — the Supabase Settings layout. The page owns the active value + setter.
const SubNavContext = createContext(null)

export function SubNavProvider({ children }) {
  const [subNav, setSubNav] = useState(null) // { sections, value, onChange } | null
  return (
    <SubNavContext.Provider value={{ subNav, setSubNav }}>
      {children}
    </SubNavContext.Provider>
  )
}

export function useSubNavState() {
  return useContext(SubNavContext)
}

/**
 * Page hook — register this page's sub-sections for the shell's sub-bar.
 * Pass a STABLE `sections` array (module constant) + the active `value` +
 * a stable `onChange` (e.g. a useState setter).
 */
export function useSubNav(sections, value, onChange, title = null) {
  const ctx = useContext(SubNavContext)
  const set = ctx?.setSubNav

  // Update on value change — no cleanup here, so switching tabs doesn't flicker
  // the bar away.
  useEffect(() => {
    set?.({ sections, value, onChange, title })
  }, [set, sections, value, onChange, title])

  // Clear only when the page unmounts.
  useEffect(() => {
    return () => set?.(null)
  }, [set])
}
