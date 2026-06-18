import { MoreHorizontal } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { cn } from "@/lib/utils"

/**
 * ActionMenu — a "⋯ More" trigger that opens a DropdownMenu of actions.
 *
 * Props:
 *   items: Array<{
 *     label: string,
 *     onSelect: () => void,
 *     icon?: ReactNode,       — optional lucide icon element
 *     destructive?: boolean,  — renders the item in destructive style
 *     separator?: boolean,    — insert a separator BEFORE this item
 *     disabled?: boolean,
 *   }>
 *   triggerLabel?: string  — accessible label for the trigger (default: "More actions")
 *   align?: "start" | "end" | "center"
 *   className? — extra class on the trigger button
 */
function ActionMenu({
  items = [],
  triggerLabel = "More actions",
  align = "end",
  className,
  ...props
}) {
  return (
    <DropdownMenu {...props}>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon-sm"
          aria-label={triggerLabel}
          className={cn("shrink-0", className)}
        >
          <MoreHorizontal className="size-4" aria-hidden="true" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align={align}>
        {items.map((item, idx) => (
          <div key={idx}>
            {item.separator && idx > 0 && <DropdownMenuSeparator />}
            <DropdownMenuItem
              onSelect={item.onSelect}
              disabled={item.disabled}
              variant={item.destructive ? "destructive" : "default"}
              className="gap-2"
            >
              {item.icon && (
                <span aria-hidden="true" className="shrink-0">
                  {item.icon}
                </span>
              )}
              {item.label}
            </DropdownMenuItem>
          </div>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

export { ActionMenu }
