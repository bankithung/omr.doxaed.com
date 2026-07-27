import { cn } from "@/lib/utils"

/**
 * Card — flat workhorse surface for detail / settings / dashboard screens.
 * Depth comes from a hairline border plus a surface fill, never a gradient.
 * Hover raises the soft ink lift fet uses on every card and panel.
 */
function Card({ className, ...props }) {
  return (
    <div
      data-slot="card"
      className={cn(
        "ink-lift rounded-lg border border-border bg-card text-card-foreground",
        className
      )}
      {...props}
    />
  )
}

/**
 * Panel — one solid, non transparent section used to group a page body.
 * Same surface and hairline as Card with roomier padding.
 */
function Panel({ className, ...props }) {
  return (
    <div
      data-slot="panel"
      className={cn(
        "ink-lift rounded-lg border border-border bg-card p-5 md:p-6",
        className
      )}
      {...props}
    />
  )
}

function CardHeader({ className, ...props }) {
  return (
    <div
      data-slot="card-header"
      className={cn(
        "flex items-center justify-between gap-2 border-b border-border px-4 py-3",
        className
      )}
      {...props}
    />
  )
}

function CardTitle({ className, children, ...props }) {
  return (
    <h3
      data-slot="card-title"
      className={cn("text-sm font-medium", className)}
      {...props}
    >
      {children}
    </h3>
  )
}

function CardDescription({ className, ...props }) {
  return (
    <p
      data-slot="card-description"
      className={cn("text-sm text-muted-foreground", className)}
      {...props}
    />
  )
}

function CardContent({ className, ...props }) {
  return (
    <div data-slot="card-content" className={cn("p-4", className)} {...props} />
  )
}

function CardFooter({ className, ...props }) {
  return (
    <div
      data-slot="card-footer"
      className={cn(
        "flex items-center justify-end gap-2 border-t border-border bg-surface-2 px-4 py-3",
        className
      )}
      {...props}
    />
  )
}

export { Card, Panel, CardHeader, CardTitle, CardDescription, CardContent, CardFooter }
