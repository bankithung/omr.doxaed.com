import { cn } from "@/lib/utils"

function Input({
  className,
  type,
  ...props
}) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        /* fet field: white ground so editable controls separate from the card
           they sit on, ink border that darkens on hover, indigo ring on focus. */
        "h-8 w-full min-w-0 rounded-lg border border-input bg-[var(--field)] px-2.5 py-1 text-sm transition-[border-color,box-shadow] outline-none file:inline-flex file:h-6 file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-[var(--field-placeholder)] hover:not-disabled:not-read-only:border-[var(--field-border-hover)] focus-visible:border-primary focus-visible:ring-3 focus-visible:ring-ring disabled:pointer-events-none disabled:cursor-not-allowed disabled:border-border disabled:bg-[var(--field-disabled)] disabled:text-muted-foreground read-only:bg-[var(--field-disabled)] aria-invalid:border-destructive aria-invalid:bg-destructive/[0.07]",
        className
      )}
      {...props} />
  );
}

export { Input }
