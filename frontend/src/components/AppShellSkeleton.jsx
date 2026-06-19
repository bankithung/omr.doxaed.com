import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"

/**
 * AppShellSkeleton — a static, flat placeholder for the authenticated two-level
 * app shell, shown while the auth probe + lazy route chunk load on a refresh
 * inside the app. It mirrors AppShell's anatomy (w-14 primary rail + w-60
 * secondary panel + a 56px top bar + a content area) so the swap to the real
 * shell causes minimal layout shift and a refresh never flashes a bare
 * "Loading…" string.
 *
 * Reduced-motion-safe: every shimmer is `motion-reduce:animate-none`, so it
 * renders as a calm set of gunmetal blocks for users who prefer reduced motion.
 */

const pulse = "motion-reduce:animate-none"

function RailDot() {
  return <Skeleton className={cn("size-9 rounded-md", pulse)} />
}

function NavRowSkeleton({ w = "w-28" }) {
  return (
    <div className="flex min-h-[40px] items-center gap-2.5 px-2.5">
      <Skeleton className={cn("size-4 shrink-0 rounded", pulse)} />
      <Skeleton className={cn("h-3.5 rounded", w, pulse)} />
    </div>
  )
}

export default function AppShellSkeleton() {
  return (
    <div
      aria-hidden="true"
      className="flex min-h-screen bg-canvas text-foreground"
    >
      {/* Primary icon rail (w-14) */}
      <aside className="hidden w-14 shrink-0 flex-col items-center gap-1.5 border-r border-strong bg-canvas py-2 lg:flex">
        <Skeleton className={cn("mb-1 size-9 rounded-md", pulse)} />
        {Array.from({ length: 5 }).map((_, i) => (
          <RailDot key={i} />
        ))}
        <div className="mt-auto flex flex-col items-center gap-1.5">
          <RailDot />
          <RailDot />
        </div>
      </aside>

      {/* Secondary contextual panel (w-60) */}
      <aside className="hidden w-60 shrink-0 flex-col border-r border-strong bg-surface-1 lg:flex">
        <div className="flex h-14 items-center gap-2 border-b border-border px-4">
          <Skeleton className={cn("h-4 w-28 rounded", pulse)} />
        </div>
        <div className="space-y-1 py-3">
          <div className="px-4 pb-1">
            <Skeleton className={cn("h-2.5 w-16 rounded", pulse)} />
          </div>
          <NavRowSkeleton w="w-32" />
          <NavRowSkeleton w="w-24" />
          <NavRowSkeleton w="w-28" />
          <NavRowSkeleton w="w-20" />
          <div className="px-4 pb-1 pt-3">
            <Skeleton className={cn("h-2.5 w-16 rounded", pulse)} />
          </div>
          <NavRowSkeleton w="w-28" />
          <NavRowSkeleton w="w-24" />
        </div>
        <div className="mt-auto border-t border-border p-2">
          <Skeleton className={cn("h-10 w-full rounded-md", pulse)} />
        </div>
      </aside>

      {/* Main column: top bar + content */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex min-h-[56px] items-center gap-2 bg-background/85 px-3 backdrop-blur-sm sm:px-4">
          {/* mobile menu / breadcrumb */}
          <Skeleton className={cn("size-9 rounded-md lg:hidden", pulse)} />
          <Skeleton className={cn("hidden h-4 w-40 rounded sm:block", pulse)} />
          <div className="ml-auto flex items-center gap-2">
            <Skeleton className={cn("hidden h-8 w-40 rounded-md md:block", pulse)} />
            <Skeleton className={cn("hidden h-8 w-32 rounded-md sm:block", pulse)} />
            <Skeleton className={cn("size-8 rounded-full", pulse)} />
          </div>
        </header>

        <main className="flex-1 overflow-auto p-4 pb-16 sm:p-6 lg:pb-6">
          <div className="mx-auto w-full max-w-6xl space-y-6">
            {/* Page header */}
            <div className="space-y-2">
              <Skeleton className={cn("h-6 w-56 rounded", pulse)} />
              <Skeleton className={cn("h-4 w-80 max-w-full rounded", pulse)} />
            </div>

            {/* Stat cards */}
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <div
                  key={i}
                  className="flex min-w-0 flex-col gap-2 rounded-lg border border-border bg-card p-4"
                >
                  <Skeleton className={cn("h-3 w-16 rounded", pulse)} />
                  <Skeleton className={cn("h-7 w-12 rounded", pulse)} />
                </div>
              ))}
            </div>

            {/* Table-ish block */}
            <div className="overflow-hidden rounded-lg border border-border">
              <div className="flex h-9 items-center gap-3 border-b border-border bg-surface-1 px-3">
                <Skeleton className={cn("h-3 w-24 rounded", pulse)} />
                <Skeleton className={cn("ml-auto h-3 w-16 rounded", pulse)} />
              </div>
              {Array.from({ length: 6 }).map((_, i) => (
                <div
                  key={i}
                  className={cn(
                    "flex h-11 items-center gap-3 px-3",
                    i !== 5 && "border-b border-border"
                  )}
                >
                  <Skeleton className={cn("h-4 max-w-[180px] flex-1 rounded", pulse)} />
                  <Skeleton className={cn("h-4 w-24 rounded", pulse)} />
                  <Skeleton className={cn("ml-auto h-4 w-10 rounded", pulse)} />
                </div>
              ))}
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}
