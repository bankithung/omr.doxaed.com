import { cva } from "class-variance-authority";
import { Slot } from "radix-ui"

import { cn } from "@/lib/utils"

/* fet's .btn: a 5px chip on the tray surface with a hairline ink border, an
   indigo wash on hover and a 0.98 press. The primary action is the solid
   indigo chip with white text. */
const buttonVariants = cva(
  "group/button inline-flex shrink-0 items-center justify-center rounded-lg border border-border bg-clip-padding text-sm font-medium whitespace-nowrap transition-[background-color,border-color,color,transform,box-shadow] ease-out duration-150 outline-0 select-none focus-visible:ring-3 focus-visible:ring-ring focus-visible:border-primary active:scale-[0.98] disabled:pointer-events-none disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default:
          "bg-primary text-primary-foreground border-primary font-semibold hover:bg-[var(--primary-hover)] hover:border-[var(--primary-hover)]",
        outline:
          "border-border bg-secondary text-foreground hover:bg-accent hover:border-muted-foreground aria-expanded:bg-accent aria-expanded:text-foreground",
        secondary:
          "border-border bg-secondary text-foreground hover:bg-accent hover:border-muted-foreground aria-expanded:bg-accent aria-expanded:text-foreground",
        ghost:
          "border-transparent bg-transparent text-muted-foreground shadow-none hover:bg-accent hover:text-foreground hover:border-transparent aria-expanded:bg-accent aria-expanded:text-foreground",
        destructive:
          "border-border bg-secondary text-destructive hover:border-destructive hover:bg-destructive/[0.08]",
        warning:
          "border-border bg-secondary text-[var(--color-warning)] hover:border-[var(--color-warning)] hover:bg-[var(--color-warning)]/[0.08]",
        link: "border-transparent bg-transparent text-foreground underline underline-offset-2 hover:text-[var(--accent-solid)]",
      },
      size: {
        default:
          "h-8 gap-1.5 px-3 has-data-[icon=inline-end]:pr-2.5 has-data-[icon=inline-start]:pl-2.5",
        xs: "h-6 gap-1 rounded-sm px-2 text-xs has-data-[icon=inline-end]:pr-1.5 has-data-[icon=inline-start]:pl-1.5 [&_svg:not([class*='size-'])]:size-3",
        sm: "h-7 gap-1 rounded-md px-2.5 text-xs has-data-[icon=inline-end]:pr-1.5 has-data-[icon=inline-start]:pl-1.5 [&_svg:not([class*='size-'])]:size-3.5",
        lg: "h-9 gap-1.5 px-4 has-data-[icon=inline-end]:pr-3 has-data-[icon=inline-start]:pl-3",
        icon: "size-8",
        "icon-xs": "size-6 rounded-sm [&_svg:not([class*='size-'])]:size-3",
        "icon-sm": "size-7 rounded-md",
        "icon-lg": "size-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant = "default",
  size = "default",
  asChild = false,
  ...props
}) {
  const Comp = asChild ? Slot.Root : "button"

  return (
    <Comp
      data-slot="button"
      data-variant={variant}
      data-size={size}
      className={cn(buttonVariants({ variant, size, className }))}
      {...props} />
  );
}

export { Button, buttonVariants }
