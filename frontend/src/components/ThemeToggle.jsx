import { useEffect, useState } from "react"
import { useTheme } from "next-themes"
import { SunIcon, MoonIcon } from "lucide-react"

import { Button } from "@/components/ui/button"

/**
 * ThemeToggle — flat icon button that flips light/dark (class strategy on <html>).
 * Renders a stable placeholder until mounted to avoid hydration/SSR flicker.
 */
export function ThemeToggle({ className }) {
  const [mounted, setMounted] = useState(false)
  const { resolvedTheme, setTheme } = useTheme()

  useEffect(() => setMounted(true), [])

  const isDark = resolvedTheme === "dark"

  return (
    <Button
      variant="ghost"
      size="icon-sm"
      className={className}
      aria-label={isDark ? "Switch to light theme" : "Switch to dark theme"}
      onClick={() => setTheme(isDark ? "light" : "dark")}
    >
      {mounted && isDark ? (
        <MoonIcon className="size-4" aria-hidden="true" />
      ) : (
        <SunIcon className="size-4" aria-hidden="true" />
      )}
    </Button>
  )
}
