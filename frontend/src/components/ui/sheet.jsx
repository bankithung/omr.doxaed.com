"use client"

import { Dialog as DialogPrimitive } from "radix-ui"
import { cn } from "@/lib/utils"
import { XIcon } from "lucide-react"
import { Button } from "@/components/ui/button"

/**
 * Sheet — a side-anchored panel built on Radix Dialog.
 * side: "left" | "right" (default "left")
 *
 * Usage:
 *   <Sheet open={open} onOpenChange={setOpen}>
 *     <SheetContent side="left">…</SheetContent>
 *   </Sheet>
 */

function Sheet({ ...props }) {
  return <DialogPrimitive.Root data-slot="sheet" {...props} />
}

function SheetTrigger({ ...props }) {
  return <DialogPrimitive.Trigger data-slot="sheet-trigger" {...props} />
}

function SheetClose({ ...props }) {
  return <DialogPrimitive.Close data-slot="sheet-close" {...props} />
}

function SheetPortal({ ...props }) {
  return <DialogPrimitive.Portal data-slot="sheet-portal" {...props} />
}

function SheetOverlay({ className, ...props }) {
  return (
    <DialogPrimitive.Overlay
      data-slot="sheet-overlay"
      className={cn(
        "fixed inset-0 z-50 bg-black/40 duration-200",
        "data-open:animate-in data-open:fade-in-0",
        "data-closed:animate-out data-closed:fade-out-0",
        className,
      )}
      {...props}
    />
  )
}

function SheetContent({ side = "left", className, children, ...props }) {
  const sideStyles = {
    left: cn(
      "left-0 top-0 h-full w-72 max-w-[85vw] border-r",
      "data-open:slide-in-from-left data-closed:slide-out-to-left",
    ),
    right: cn(
      "right-0 top-0 h-full w-72 max-w-[85vw] border-l",
      "data-open:slide-in-from-right data-closed:slide-out-to-right",
    ),
  }

  return (
    <SheetPortal>
      <SheetOverlay />
      <DialogPrimitive.Content
        data-slot="sheet-content"
        className={cn(
          "fixed z-50 flex flex-col bg-sidebar text-sidebar-foreground shadow-xl",
          "duration-200 data-open:animate-in data-closed:animate-out",
          sideStyles[side] ?? sideStyles.left,
          className,
        )}
        {...props}
      >
        {children}
        <DialogPrimitive.Close asChild>
          <Button
            variant="ghost"
            size="icon-sm"
            className="absolute top-3 right-3 text-sidebar-foreground hover:bg-sidebar-accent"
            aria-label="Close menu"
          >
            <XIcon className="size-4" />
          </Button>
        </DialogPrimitive.Close>
      </DialogPrimitive.Content>
    </SheetPortal>
  )
}

function SheetHeader({ className, ...props }) {
  return (
    <div
      data-slot="sheet-header"
      className={cn("flex flex-col gap-1 border-b border-sidebar-border px-4 py-3", className)}
      {...props}
    />
  )
}

function SheetTitle({ className, ...props }) {
  return (
    <DialogPrimitive.Title
      data-slot="sheet-title"
      className={cn("text-sm font-semibold text-sidebar-foreground", className)}
      {...props}
    />
  )
}

export { Sheet, SheetClose, SheetContent, SheetHeader, SheetOverlay, SheetPortal, SheetTitle, SheetTrigger }
