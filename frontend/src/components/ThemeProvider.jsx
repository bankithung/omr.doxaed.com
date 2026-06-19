import { ThemeProvider as NextThemesProvider } from "next-themes"

/**
 * ThemeProvider — class strategy on <html> (adds/removes `.dark`), persisted to
 * localStorage. Wraps next-themes (already a dependency and used by sonner).
 * Mounted once at the app root.
 */
export function ThemeProvider({ children }) {
  return (
    <NextThemesProvider
      attribute="class"
      defaultTheme="dark"
      enableSystem
      disableTransitionOnChange
    >
      {children}
    </NextThemesProvider>
  )
}
