/**
 * SectionContainer — the repeated vertical rhythm of the marketing page
 * (Supabase's `SectionContainer`). Centered, max-width-capped, generous
 * responsive vertical padding. Pass `className` to tune a specific section.
 */
export default function SectionContainer({ className = "", children, ...props }) {
  return (
    <section
      className={`relative mx-auto w-full max-w-[90rem] px-6 py-16 sm:py-[4.5rem] md:py-24 lg:px-16 xl:px-20 ${className}`}
      {...props}
    >
      {children}
    </section>
  )
}
