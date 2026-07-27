import { ThemeProvider as NextThemesProvider } from "next-themes"

/**
 * ThemeProvider — the design system this app shares with Doxaed Timetables is
 * light only, so the theme is forced to light. Keeping the provider mounted
 * means sonner and anything else reading next-themes still resolves cleanly,
 * and a stale `dark` value in localStorage cannot flip the app.
 */
export function ThemeProvider({ children }) {
  return (
    <NextThemesProvider
      attribute="class"
      defaultTheme="light"
      forcedTheme="light"
      enableSystem={false}
      disableTransitionOnChange
    >
      {children}
    </NextThemesProvider>
  )
}
