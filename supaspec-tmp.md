I now have everything I need: the full token system, components, the cinematic landing (with all its gradients/glow), the auth layout, the app shell, the frozen E2E names, the owner's NO-gradients rule, and the existing font stack (Geist Variable already self-hosted — not Figtree). 

I have enough to produce the complete build-ready spec. Let me compile it.

---

# DoxaEd OMR → Supabase Re-Theme: BUILD-READY SPEC

## 0. Grounding facts (verified against the live codebase)

- **Stack confirmed:** React 19 + Vite 8 + Tailwind v4 (`@tailwindcss/vite`) + shadcn JSX. Tokens live in `frontend/src/index.css` using `@theme` / `@theme inline` + `:root` / `.dark` oklch vars. shadcn reads `cssVariables:true`, `baseColor:neutral`.
- **Fonts already self-hosted:** `@fontsource-variable/geist` (sans, app-wide via `@layer base html { @apply font-sans }`), `@fontsource/geist-mono`, `@fontsource/instrument-serif` (landing only). **Figtree is NOT installed.** Geist Variable is a geometric-grotesque and is the right Circular substitute — **recommendation: KEEP Geist, do not add Figtree** (it's an unnecessary swap; Geist already delivers the Supabase "custom-font" feel). The spec below gives the Figtree path as an *optional* alternative but recommends Geist.
- **Current default theme:** `next-themes` `defaultTheme="light"` (`frontend/src/components/ThemeProvider.jsx:13`). The whole app currently boots light.
- **OWNER NON-NEGOTIABLE (CLAUDE.md):** *"NO gradients anywhere — flat solid colors."* The existing `.landing-cinematic` (index.css lines 232-428: aurora, conic beam, glass, grain, vignette, cursor-glow, marquee gradients) **violates this** and is what the owner now wants replaced by the cleaner flat Supabase aesthetic. **The re-theme is the licence to delete the cinematic layer.**
- **Brand decision input:** DoxaEd is an OMR/exam product where green = "correct answer" grading semantics. Current brand is **indigo** (`--primary: oklch(0.488 0.243 264.376)`).
- **FROZEN E2E accessible names** (from `e2e/run.mjs` — these strings/roles MUST survive the re-theme): `heading /Grade a stack of bubble sheets/`, `button "Create account"`, text `"Email verified"`, `heading /Welcome back/`, `button "Sign in"`, `button "Create class"` + `dialog` + `button "Create"`, text `"Class created"`, `button "Next: Add questions"`, `button "+ Add question"`, `button "+ Add option"`, `button "Save question"`, text `"Saved"`, `button "Next: Review"`, `button "Finish & mark ready"`, `button "Create roster"`, text `"Roster created"`, `button "Add student"` + placeholders `"e.g. Asha Devi"` / `"e.g. 101"`, `button "Generate sheets"` / `"Generate"` + text `"Sheets generated successfully!"`, `button /Upload & scan/` + text `"processed successfully"`, `link "Detail"`, `heading "Analytics"`, text `"Score distribution"`, `button /Download all report cards/i`, `tab /Item Analysis/i`, `button "Get result"`, text `"Roll number mismatch"`. **Re-theming touches only `className`/visuals — never these `name=`/`children` strings, roles, or placeholders.**

---

## 1. DESIGN TOKENS — exact `src/index.css` rewrite

### 1.1 Brand decision (pick ONE) — **RECOMMENDATION: BRAND-SWAP MODE = keep DoxaEd INDIGO as `--primary`**

**Rationale:** Supabase's premium look is ~80% the achromatic gunmetal neutral ramp + 1px hairline borders + one disciplined accent + restrained type — *not* the specific green hue. For an OMR/exam app, green is load-bearing grading semantics (correct vs wrong). Cloning Supabase-green into `--primary` collides with the answer-key UI. Indigo (hue ~264) sits far from success-green (hue ~150-160), giving clean semantic separation. Supabase even ships this exact indigo as its own `--secondary` (`#6a66ff`), so the swap stays "Supabase-native." **Adopt Supabase's *pattern* (one accent, used only for primary buttons / focus ring / links / active-nav / chart-1 / 10%-alpha tints), not its hue.**

- Keep `--primary: oklch(0.488 0.243 264.376)` (light) / `oklch(0.65 0.18 264)` (dark) — already in place. Nudge dark primary slightly brighter for the dark-first canvas (see below).
- Reserve green exclusively for `--color-success` (already `oklch(0.527 0.154 150)` ≈ Supabase Radix-green `#30a46c`). Map CORRECT→success, WRONG→destructive.
- **If the owner instead wants the pixel-faithful Supabase clone (EXACT-MATCH MODE):** set `--primary: oklch(0.776 0.155 162.5)` (=#3fcf8e) with `--primary-foreground: oklch(0.205 0 0)` (near-black #161616), and shift `--color-success` to `oklch(0.70 0.17 150)` to avoid clash. Not recommended for the product.

### 1.2 Dark-first default

Supabase boots dark (`<html data-theme="dark">`). Flip the default so the entire app inherits the gunmetal look with zero per-page edits:

- `frontend/src/components/ThemeProvider.jsx`: change `defaultTheme="light"` → `defaultTheme="dark"`. Keep `enableSystem` if you want OS preference to still win; set `enableSystem={false}` for a hard dark-default. **Recommend `defaultTheme="dark"` + keep `enableSystem`** (so users who prefer light still get the tuned light variant).
- `frontend/index.html`: add `class="dark" style="color-scheme:dark"` to `<html>` to prevent a light flash before hydration: `<html lang="en" class="dark" style="color-scheme:dark">`.

### 1.3 The token rewrite

Replace the `:root` and `.dark` blocks (index.css lines 87-207) with the Supabase-tuned values below. **Key changes:** drop neutral chroma from `0.004-0.006` toward `0` (Supabase grays are pure achromatic `0deg 0% L%`); retune the dark neutral L-steps to Supabase's exact ladder (#0f0f0f → #1f1f1f → #292929) and dark borders to #2e2e2e/#3e3e3e; add a 6th tertiary text token + a brand-glow + white-alpha hairline utility. The `@theme` / `@theme inline` blocks (lines 10-85) and the `@layer base`/`@utility` blocks (209-230) **stay as-is** (they already wire `--color-*`, radius calc chain, `font-sans`, `tabular`, `tracking-tight-1`).

```css
:root {
  /* ── LIGHT (the alternate). Supabase light: near-white #fcfcfc canvas. ── */
  --background: oklch(0.985 0 0);            /* #fcfcfc page */
  --foreground: oklch(0.205 0 0);           /* #171717 gray-light-1200 */

  --canvas:    oklch(0.985 0 0);            /* app canvas */
  --surface-1: oklch(1 0 0);               /* #ffffff cards (surface-75) */
  --surface-2: oklch(0.985 0 0);           /* #fcfcfc popovers (surface-100) */
  --surface-3: oklch(0.967 0 0);           /* #f3f3f3 nested */

  --card: oklch(1 0 0);
  --card-foreground: oklch(0.205 0 0);
  --popover: oklch(0.985 0 0);
  --popover-foreground: oklch(0.205 0 0);

  /* Brand — DoxaEd indigo (UNCHANGED). Accent ONLY. */
  --primary: oklch(0.488 0.243 264.376);
  --primary-foreground: oklch(0.985 0 0);
  --secondary: oklch(0.97 0 0);
  --secondary-foreground: oklch(0.27 0 0);
  --muted: oklch(0.97 0 0);
  --muted-foreground: oklch(0.556 0 0);     /* #898989-ish secondary text */
  --foreground-lighter: oklch(0.65 0 0);    /* NEW: tertiary/placeholder #b2b2b2 */

  --accent: oklch(0.9 0.04 195);            /* teal — CHARTS ONLY (demoted) */
  --accent-foreground: oklch(0.3 0.06 195);
  --destructive: oklch(0.637 0.205 25.3);   /* #e54d2e Supabase tomato */

  /* Borders — Supabase light hairlines #dfdfdf / #d4d4d4 / #8f8f8f */
  --border: oklch(0.9 0 0);                 /* #dfdfdf default */
  --border-strong: oklch(0.87 0 0);         /* #d4d4d4 structural */
  --border-stronger: oklch(0.66 0 0);       /* #8f8f8f hover/active */
  --input: oklch(0.9 0 0);
  --ring: oklch(0.488 0.243 264.376);

  --nav-active-bg: oklch(0.955 0.01 264);   /* faint tinted, not saturated */
  --nav-active-fg: var(--primary);

  /* Charts — sequential indigo → teal (unchanged) */
  --chart-1: oklch(0.488 0.243 264.376);
  --chart-2: oklch(0.55 0.18 230);
  --chart-3: oklch(0.56 0.16 195);
  --chart-4: oklch(0.62 0.12 160);
  --chart-5: oklch(0.70 0.10 140);

  --radius: 0.5rem;                          /* 8px workhorse — ALREADY matches Supabase */

  --sidebar: oklch(1 0 0);
  --sidebar-foreground: oklch(0.27 0 0);
  --sidebar-primary: oklch(0.488 0.243 264.376);
  --sidebar-primary-foreground: oklch(0.985 0 0);
  --sidebar-accent: oklch(0.955 0.01 264);
  --sidebar-accent-foreground: oklch(0.3 0.08 264.376);
  --sidebar-border: oklch(0.87 0 0);
  --sidebar-ring: oklch(0.488 0.243 264.376);

  /* Supabase keeps light shadows low-alpha & soft (10% black) */
  --shadow-overlay: 0 1px 2px oklch(0 0 0 / 0.05),
                    0 4px 12px oklch(0 0 0 / 0.1);

  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-standard: cubic-bezier(0.4, 0, 0.2, 1);
  --dur-fast: 130ms;
  --dur: 180ms;
}

.dark {
  /* ── DARK (DEFAULT). Supabase achromatic gunmetal, chroma → 0. ── */
  --background: oklch(0.145 0 0);            /* #0f0f0f page (alternative-default) */
  --foreground: oklch(0.985 0 0);           /* #fafafa */

  --canvas:    oklch(0.165 0 0);            /* #121212 dash-canvas */
  --surface-1: oklch(0.205 0 0);           /* #1f1f1f cards (surface-100) */
  --surface-2: oklch(0.225 0 0);           /* #242424 muted/control (popovers) */
  --surface-3: oklch(0.245 0 0);           /* #292929 surface-300 */

  --card: oklch(0.205 0 0);                 /* #1f1f1f */
  --card-foreground: oklch(0.985 0 0);
  --popover: oklch(0.205 0 0);              /* Supabase dialog = surface, not raised */
  --popover-foreground: oklch(0.985 0 0);

  --primary: oklch(0.66 0.2 264.376);       /* indigo, nudged brighter for dark canvas */
  --primary-foreground: oklch(0.985 0 0);
  --secondary: oklch(0.225 0 0);            /* #242424 */
  --secondary-foreground: oklch(0.985 0 0);
  --muted: oklch(0.225 0 0);                /* #242424 control/muted */
  --muted-foreground: oklch(0.72 0 0);      /* #b4b4b4 — NOT pure white (key Supabase calm) */
  --foreground-lighter: oklch(0.6 0 0);     /* NEW: #898989 placeholder/tertiary */

  --accent: oklch(0.28 0.04 195);           /* teal — charts only */
  --accent-foreground: oklch(0.85 0.06 195);
  --destructive: oklch(0.637 0.205 25.3);   /* #e54d2e */

  /* SOLID gunmetal borders — the single biggest premium lever (Supabase #2e2e2e/#3e3e3e) */
  --border: oklch(0.27 0 0);                /* #2e2e2e default */
  --border-strong: oklch(0.32 0 0);         /* #363636 strong */
  --border-stronger: oklch(0.37 0 0);       /* #454545 stronger/hover */
  --input: oklch(0.27 0 0);
  --ring: oklch(0.66 0.2 264.376);

  --nav-active-bg: oklch(0.245 0.02 264);   /* faint indigo-tinted fill */
  --nav-active-fg: oklch(0.78 0.12 264.376);

  --chart-1: oklch(0.66 0.2 264.376);
  --chart-2: oklch(0.66 0.15 230);
  --chart-3: oklch(0.67 0.13 195);
  --chart-4: oklch(0.70 0.10 160);
  --chart-5: oklch(0.75 0.09 140);

  --sidebar: oklch(0.165 0 0);              /* #121212 dash-sidebar (Supabase: sidebar ≈ canvas) */
  --sidebar-foreground: oklch(0.85 0 0);
  --sidebar-primary: oklch(0.66 0.2 264.376);
  --sidebar-primary-foreground: oklch(0.985 0 0);
  --sidebar-accent: oklch(0.245 0.02 264);
  --sidebar-accent-foreground: oklch(0.82 0.1 264.376);
  --sidebar-border: oklch(0.27 0 0);        /* = --border */
  --sidebar-ring: oklch(0.66 0.2 264.376);

  --shadow-overlay: none;                    /* dark = border + surface step, never glow */
}
```

### 1.4 New tokens to expose in `@theme inline` (add to the block at lines 28-85)

```css
  --color-foreground-lighter: var(--foreground-lighter);  /* tertiary / placeholder text */
```

### 1.5 White-alpha hairline + brand-glow utilities (add near the `@utility` block, ~line 224)

Supabase's signature is white-at-low-opacity borders that read consistently over any dark surface, plus one brand focus-glow. **These are flat (no gradient) → owner-rule compliant.**

```css
/* Supabase-style white-alpha hairline — consistent edge over any dark surface */
@utility border-hairline { border-color: oklch(1 0 0 / 0.08); }
/* Brand focus glow (echoes Supabase #2cf494 ring geometry, recolored to indigo) */
@utility ring-brand-glow {
  box-shadow: 0 0 0 1px var(--ring), 0 0 6px 0 oklch(0.66 0.2 264 / 0.4);
}
```

### 1.6 Radii / spacing / shadows — **ALREADY ALIGNED, do not touch**

- **Radius:** `--radius: 0.5rem` (8px) is exactly Supabase's most-used component radius. The `@theme inline` calc chain (lines 78-84) already derives sm/md/lg/xl. Buttons currently `rounded-lg` (8px) — Supabase uses `rounded-md` (6px) on buttons; this is a *component-recipe* nuance, handled in §3, not a token change.
- **Spacing:** Tailwind v4 default `--spacing:.25rem` (4px) — identical to Supabase. No change. Adopt the rhythm in markup: `gap-2`/`p-2` (8px) intra-component, `p-4`/`p-6` cards, `py-24` between landing sections.
- **Type scale:** index.css lines 11-16 currently *override* `--text-*` to px values (xs 12 / sm 14 / base 16 / lg 20 / xl 24 / 2xl 32). Supabase uses **Tailwind v4 defaults unchanged** (lg 18px, xl 20px, 2xl 24px, plus 3xl-7xl). See §2.2 — **recommend removing these overrides** so the full Supabase scale (incl. line-heights) is inherited and `text-7xl` hero works.
- **Shadows:** Tailwind v4 default shadow scale is identical to Supabase's (low-alpha 10% black). Keep using `shadow-sm` resting / `shadow-md` hover / `shadow-lg`/`xl` for popovers+modals. `--shadow-overlay` (overlay components) stays soft in light, `none` in dark.

---

## 2. TYPOGRAPHY — applied globally (app + landing + auth)

### 2.1 Font loading — **RECOMMEND: keep Geist (already self-hosted)**

Geist Variable is already imported app-wide (`@import "@fontsource-variable/geist"` at index.css:4) and wired as `--font-sans` / `--font-heading` (lines 30-31). It is a geometric-grotesque — the correct open Circular substitute. **No font install needed; this is the biggest fidelity win for free.**

- **Mono:** `@fontsource/geist-mono` is installed but currently imported **only in the landing chunk** (`Landing.jsx`). To make mono available app-wide for OMR data (scores, roll numbers, exam IDs, answer keys), add to `src/main.jsx`: `import "@fontsource/geist-mono/400.css"` + `/500.css`, and add `--font-mono: 'Geist Mono', ui-monospace, 'SFMono-Regular', Menlo, monospace;` to the `@theme inline` block. Then `font-mono` + the existing `tabular` utility cover all numeric/code cells.
- **Optional Figtree path (NOT recommended):** `npm i @fontsource-variable/figtree`, `import '@fontsource-variable/figtree'` in `main.jsx`, set `--font-sans: 'Figtree Variable', 'Helvetica Neue', Helvetica, Arial, sans-serif`. Only do this if the owner explicitly wants Figtree over Geist; otherwise it's churn.

### 2.2 Type scale — remove the px overrides, inherit Tailwind v4 defaults

Edit index.css lines 11-16: **delete** the six `--text-*` overrides. Tailwind v4 ships the exact Supabase scale *with* paired line-heights (xs .75rem/1.33, sm .875rem/1.43, base 1rem/1.5, lg 1.125rem/1.56, xl 1.25rem/1.4, 2xl 1.5rem/1.33, 3xl 1.875/1.2, 4xl 2.25/1.11, 5xl 3/1, 6xl 3.75/1, 7xl 4.5/1). Removing the overrides unlocks `text-3xl`…`text-7xl` (needed for the hero) and the calc'd line-heights.

- Audit risk: the current app uses `text-lg` expecting **20px** and `text-xl` expecting **24px**; defaults make them **18px/20px**. Grep `text-lg|text-xl|text-2xl` in `src/routes` + `src/components`; most are headings that read fine one notch smaller (and match Supabase's denser scale). Spot-fix any that look wrong by bumping the class (`text-xl`→`text-2xl`).

### 2.3 Global type application

- **Body base:** `text-base` (16px) for prose; **`text-sm` (14px) is the app-UI workhorse** (table cells, form labels, buttons) — already encoded via `.app-density { font-size:14px }` on the shell wrapper (index.css:221). Keep that.
- **Weights:** restrain to **400 / 500 / 600** (Geist Variable covers all). No 700+ "black" weights — Supabase never uses bold heroes. Buttons/labels = `font-medium` (500); headings ≤ `font-semibold` (600).
- **Headings:** add `tracking-tight` (-0.025em) on `text-3xl`+ (hero/section titles) for Supabase headline density. The existing `.tracking-tight-1` utility (-0.01em) suits sub-headings.
- **Eyebrow/kicker (the section-labeling tell):** `text-xs font-medium uppercase tracking-widest text-muted-foreground font-mono` — used on landing section headers and could appear on app page-headers for consistency.
- **Numeric data:** `font-mono tabular` (the `tabular` @utility already exists) on scores, roll numbers, counts, IDs across Results/Analytics/StudentDetail.

---

## 3. COMPONENTS — shadcn recipes to match Supabase

All recipes use **existing semantic tokens** (so light+dark both resolve) and stay **flat (no gradient)** to honor the owner rule. Edit only `className`/`cva` strings — never role/name text.

### 3.1 Button — `src/components/ui/button.jsx`

Supabase signature: `rounded-md`, **always a 1px border** (one shade darker than fill, transparent on ghost), `text-foreground` text on the brand fill (not white), `ease-out duration-200`, **4px solid focus outline offset 1px**. Update `buttonVariants`:

- **Base string:** change `rounded-lg` → `rounded-md`; keep `border border-transparent`; swap the focus recipe to Supabase's: `focus-visible:outline-solid focus-visible:outline-4 focus-visible:outline-offset-1 focus-visible:outline-ring outline-0` (replaces `focus-visible:ring-3 ring-ring/50`); set transition to `transition-all ease-out duration-200`.
- **`default` (primary/brand):** keep `bg-primary text-primary-foreground` but add the signature 1px darker border + correct hover:
  `bg-primary text-primary-foreground border-primary hover:bg-primary/80 hover:border-primary/70`.
  *(In EXACT-MATCH green mode, `--primary-foreground` is near-black so the black-on-green reads exactly like Supabase.)*
- **`secondary`/`outline`:** `border-border-strong bg-secondary text-foreground hover:bg-surface-3 hover:border-border-stronger` — flat neutral chip, no shadow. (`border-strong`/`stronger` already resolve via `--color-strong`/`--color-stronger`, index.css:40-41.)
- **`ghost`:** `border-transparent text-muted-foreground hover:text-foreground hover:bg-surface-3 shadow-none`.
- **Sizes:** keep the current geometry; the canonical Supabase pairs are tiny `h-7 px-2.5 text-xs` (≈their h-26) and default `h-8/h-9 px-4 text-sm` (≈their h-38). Keep the existing `default`/`sm`/`xs`/`lg`/icon map — it already matches the dense feel.

### 3.2 Card — `src/components/ui/card.jsx`

Already flat (border + surface, no shadow) — minimal change. To match Supabase exactly:
- `Card`: `rounded-lg` → `rounded-xl` (12px, Supabase's card radius); add `transition-colors hover:border-border-strong` for the subtle hover affordance; keep `border border-border bg-card`.
- `CardContent` padding `p-4` → `p-6` (24px, Supabase card rhythm) on marketing/feature cards; keep `p-4` for dense app cards (make it a prop or a second variant if needed).
- **Signature gradient-border panel:** Supabase's 1px-gradient-border card *is a gradient* → **forbidden by owner rule.** Replace with a **flat equivalent** that reads almost identical: a 1px solid `border-border` card on `bg-surface-1` that goes `hover:border-border-strong hover:shadow-md`. Document this as the DoxaEd "Panel" — it captures the surface+hairline depth without the gradient. (This is exactly the reference's own fallback: the look comes from surface + hairline, not the gradient.)

### 3.3 Badge — `src/components/ui/badge.jsx`

Already pill-shaped (`rounded-full px-2.5 py-0.5 text-xs font-medium`) — matches Supabase. Tune:
- `neutral` (Supabase info pill): `rounded-full border border-border-strong bg-surface-1 px-2.5 py-1 text-xs text-muted-foreground`.
- Add a **brand/live** variant: `border border-primary/40 bg-primary/10 text-primary` and pair with the existing `StatusDot` (`size-1.5 rounded-full`) + `animate-pulse` for a live status badge.
- Keep the semantic `success/warning/error/info` variants (already color-mix on tokens) — they now inherit the Supabase Radix status hues via the retuned `--destructive`/`--color-success`.

### 3.4 Input — `src/components/ui/input.jsx`

Supabase signature: `h-[34px]`, faint `bg-foreground/[.026]` tint (not pure white), `border-input` (≈border-control), **neutral gray focus ring (not brand)**, `rounded-md`. Update the className:
- `rounded-lg` → `rounded-md`; `h-8` → `h-[34px]` (or keep `h-8`=32px for app density — close enough; Supabase forms use 34px); `bg-transparent` → `bg-foreground/[0.026]`;
- Focus: replace brand ring with Supabase's neutral ring — `focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-border-strong focus-visible:ring-offset-2 focus-visible:ring-offset-background` (subtle, non-brand). Keep `aria-invalid:border-destructive aria-invalid:bg-destructive/10`.
- `placeholder:text-muted-foreground` → `placeholder:text-foreground-lighter` (uses the new tertiary token).

### 3.5 Nav / header — landing `LandingNav.jsx` + app shell

- **Landing nav (rewrite, §4):** sticky translucent + blur, `h-16` (64px), hairline bottom border, ghost nav links, brand CTA at right. Replace the framer-motion gradient-bg nav with: `<header className="sticky top-0 z-40 border-b border-border bg-background/90 backdrop-blur-sm">` + inner `flex h-16 items-center justify-between`. Links: `text-sm text-muted-foreground hover:text-foreground transition-colors`. Drop the gradient `ScrollRail` (it's a `bg-gradient-to-r` → owner-rule violation).
- **App shell header** (`AppShell.jsx`): already token-driven; it inherits the new dark-first tokens automatically. No structural change — just confirm any hardcoded `bg-white`/`text-gray-*`/`border-zinc-*` are swapped to semantic classes (see §6 audit).

---

## 4. LANDING re-theme — replace cinematic-glow with flat Supabase shape

**This replaces the entire `.landing-cinematic` system.** Delete index.css lines 232-428 (marquee keyframes, conic beam, glass, grain, vignette, cursor-glow, display utilities) and the cinematic font re-point. Rewrite `src/routes/Landing.jsx` and its `landing/*` children to use **app semantic tokens** (so the landing now flips with the theme and is dark-first by default) and **flat surfaces + 1px borders + soft edge-fade masks only** — no gradients, no glow, no aurora, no conic beam.

### 4.1 Page architecture (Supabase DOM order, DoxaEd content)

`Nav → Hero → (logo/trust strip) → Bento feature grid → "How it works" flow → CTA band → Footer`. Reuse existing content/copy.

### 4.2 SectionContainer (the repeated rhythm)

Create `landing/SectionContainer.jsx`:
```jsx
export default function SectionContainer({ className = "", children, ...p }) {
  return (
    <section
      className={`container relative mx-auto px-6 py-16 sm:py-[4.5rem] md:py-24 lg:px-16 lg:py-24 xl:px-20 ${className}`}
      {...p}
    >{children}</section>
  )
}
```
Cap `.container` at `max-w-[96rem]`; hero copy column `max-w-2xl`; wide visual rows `max-w-[1400px]`; dashboard screenshot `max-w-6xl`.

### 4.3 Hero (preserve frozen `<h1>` text + CTAs)

The `<h1>` accessible name **must stay** `/Grade a stack of bubble sheets/`. Restyle to the Supabase two-line + accent pattern (flat):
```jsx
<section className="relative -mt-16 overflow-hidden">
  <SectionContainer className="pt-8 pb-10 md:pt-16">
    <div className="mx-auto max-w-2xl text-center">
      <h1 className="text-4xl font-medium tracking-tight text-foreground sm:text-5xl sm:leading-none lg:text-7xl">
        <span className="block">Grade a stack of bubble sheets</span>
        <span className="block text-primary">in minutes.</span>
      </h1>
      <p className="my-3 text-sm text-muted-foreground sm:mt-5 sm:text-base lg:text-lg">
        One bank. One roster. A unique sheet for every student.
      </p>
      <div className="mt-6 flex items-center justify-center gap-2">
        <Button asChild><Link to="/register">Start free</Link></Button>
        <Button variant="outline" asChild><Link to="/login">Sign in</Link></Button>
      </div>
    </div>
  </SectionContainer>
</section>
```
- Replace the `BubbleSheet` "glass-strong" hero card with a flat panel: `rounded-2xl border border-border bg-card p-2 shadow-lg`.
- Keep `KineticHeadline`'s aria-label intact OR (simpler) drop the kinetic wrapper for a plain `<h1>` — either way the accessible name regex must still match. **Verify** the `<h1>` resolves to a heading role with the matching name after the rewrite.

### 4.4 Section header pattern

```jsx
<div className="text-center">
  <span className="block font-mono text-xs uppercase tracking-widest text-muted-foreground">Why DoxaEd OMR</span>
  <h2 className="mt-3 text-[1.6rem] font-medium tracking-tight sm:text-[1.8rem] lg:text-[2rem]">Everything you need to grade faster — and fairer</h2>
  <p className="mx-auto mt-4 max-w-3xl text-lg text-muted-foreground">…</p>
</div>
```

### 4.5 Bento feature grid (12-col, flat panels)

Reuse the existing 6-item `FEATURES` array from `Bento.jsx`. Replace the cursor-spotlight gradient grid with the Supabase 12-col bento using flat Panels:
```jsx
<div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-12 xl:gap-3 2xl:gap-6">
  {/* "Per-student shuffle" = feature card */}
  <Panel className="col-span-6 md:col-span-12 xl:col-span-6 sm:h-[400px]">…</Panel>
  {/* the rest = quarter cards */}
  <Panel className="col-span-6 xl:col-span-3 sm:h-[400px]">…</Panel>
</div>
```
`Panel` = the §3.2 flat card: `rounded-xl border border-border bg-card p-6 transition-colors hover:border-border-strong hover:shadow-md`.

### 4.6 Logo/trust strip (edge-fade mask is flat-allowed)

A `linear-gradient` used purely as a **mask** (not a visible fill) is the one acceptable "gradient" — it's an opacity feather, not a colored gradient surface. If the owner reads the rule strictly, replace the mask with `[mask-image:linear-gradient(...)]` (it tints nothing) — recommend confirming, but this is standard and visually flat. Reuse the real `TRUST_POINTS` from `Footer.jsx`.

### 4.7 CTA band + Footer

- **CTA:** flat band — `<section className="border-t border-border py-24 text-center">` with the existing copy + a `<Button>` (drop the conic `landing-beam`).
- **Footer:** the existing `Footer.jsx` content (Product / OMR modes / Capabilities / Why / Get in touch columns, real mailto + doxaed.com links, Terms/Privacy) is good — restyle to tokens: swap `text-neutral-400`→`text-muted-foreground`, `text-white`→`text-foreground`, `border-white/10`→`border-border`, drop the `bg-white shadow-[0_0_36px...]` CTA button for `<Button>`, drop `font-mono-data`/`font-serif-accent` (cinematic-only classes) → `font-mono`/plain. **Keep the real links and column content.**

### 4.8 Remove the cinematic plumbing

In `Landing.jsx`: delete the `document.body.style.backgroundColor = "#05060a"` effect (the page now uses `bg-background`), remove `SmoothScroll`/`Atmosphere`/`Centerpiece`/`Marquee` cinematic imports (or keep `SmoothScroll`/Lenis if desired — it's motion, not gradient), and drop the `landing-cinematic` wrapper class. Delete now-unused files: `Atmosphere.jsx`, `Centerpiece.jsx`, `FlowSpine.jsx`, `Marquee.jsx`, `Micro.jsx` (MagneticButton/KineticHeadline glow), and the cinematic CSS block. Keep `BubbleSheet.jsx` (reused flat), `MaterialIcon.jsx`, `Analytics.jsx` (restyle flat).

---

## 5. AUTH pages — centered Supabase-style

`AuthLayout.jsx` is already a clean split layout on app tokens — it inherits dark-first automatically. Two moves to match Supabase:

1. **Switch to centered single-column** (Supabase auth is centered, not split) OR keep the branded split (acceptable). For the centered Supabase form: replace the `grid lg:grid-cols-[1.1fr_1fr]` with a single centered column:
```jsx
<div className="flex min-h-screen items-center justify-center bg-background px-4 py-12">
  <div className="w-full max-w-sm space-y-6">
    <Wordmark className="text-lg" />
    <div className="space-y-1.5">
      <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
      {subtitle && <p className="text-sm text-muted-foreground">{subtitle}</p>}
    </div>
    {/* form on a flat card */}
    <div className="rounded-xl border border-border bg-card p-6">{children}</div>
    {footer}
  </div>
</div>
```
   - **Frozen names preserved:** Login `heading "Welcome back"` + `button "Sign in"`; Register `button "Create account"`; VerifyEmail `heading "Email verified"` — all are `children`/`title` props, untouched by restyling. Keep them.
2. **VerifyEmail success block** (`VerifyEmail.jsx`): the success card uses `--color-success` color-mix (green) — correct and on-brand (green = success, not brand). Keep it; it now reads as the Supabase success state. Restyle the card to `rounded-xl border border-border bg-card` and confirm the `<h2>Email verified</h2>` text is unchanged.
3. `GoogleButton.jsx` → ensure it uses `<Button variant="outline">` so it inherits the new flat-border style.

---

## 6. PRIORITIZED BUILD ORDER

**Phase A — Tokens + fonts (everything inherits; ~1 file each):**
1. Edit `ThemeProvider.jsx` → `defaultTheme="dark"`; add `class="dark" style="color-scheme:dark"` to `index.html`.
2. Rewrite `:root` + `.dark` in `index.css` per §1.3; add `--color-foreground-lighter` to `@theme inline`; add `border-hairline` + `ring-brand-glow` utilities.
3. Remove the `--text-*` px overrides (§2.2). Add mono imports to `main.jsx` + `--font-mono` to `@theme inline` (§2.1).
   → **Smoke test:** boot app, confirm dark-first gunmetal everywhere, no light flash, borders are solid #2e2e2e, text not pure-white.

**Phase B — Components (recipe edits):**
4. `button.jsx` (rounded-md, 1px borders, Supabase focus), `input.jsx` (neutral ring, faint tint), `card.jsx` (rounded-xl + flat Panel), `badge.jsx` (brand/live variant). These propagate to every screen.

**Phase C — Landing (largest rewrite):**
5. Delete cinematic CSS + unused `landing/*` files; rewrite `Landing.jsx`, `Hero.jsx`, `LandingNav.jsx`, `Bento.jsx`, `CTA.jsx`, `Footer.jsx`, `Analytics.jsx` to flat tokens + SectionContainer. **Verify** `<h1>` name regex `/Grade a stack of bubble sheets/` survives.

**Phase D — Auth:**
6. Recenter `AuthLayout.jsx`; restyle `VerifyEmail.jsx`/`GoogleButton.jsx`. Verify `"Welcome back"`, `"Sign in"`, `"Create account"`, `"Email verified"` intact.

**Phase E — App polish (audit hardcoded colors):**
7. Grep+swap any literal colors so they pick up dark-first:
   `grep -rE "bg-white|text-white|bg-gray-|text-gray-|text-neutral-|bg-neutral-|border-zinc-|border-gray-|bg-black|#[0-9a-fA-F]{3,6}" frontend/src/routes frontend/src/components` → replace with `bg-card`/`text-foreground`/`text-muted-foreground`/`border-border`. Pay attention to `BubbleSheet.jsx`, `chart.jsx`, `StyleGuide.jsx`, any `style={{ color: ... }}`.
8. Confirm all `shadow-*` usages in dark are border-driven (dark `--shadow-overlay:none`).

### What inherits automatically (zero edits)
Every shadcn component reading semantic tokens: the two-level sidebar/app shell (`--sidebar-*`), all routes (Dashboard, Classes, TestWizard, Scan, Results, Analytics, Folders, Org*, Billing, Profile, Onboarding, AcceptInvite, PublicResult), dialogs/popovers/dropdowns/selects/tabs/tables/forms, toasts (sonner), and auth pages — all flip to dark-first gunmetal the moment Phase A lands.

### What needs explicit edits
- `index.css` tokens (Phase A) + the 4 component recipes (Phase B).
- The **entire landing** (Phase C) — it's the only part on a private cinematic theme + gradients.
- `AuthLayout`/`VerifyEmail` restyle (Phase D, optional recenter).
- Hardcoded color classes / inline hex anywhere (Phase E audit) — notably `BubbleSheet.jsx` (tint props), `LandingNav`/`Footer` neutral-* classes, `chart.jsx` series colors.

### Owner-rule + E2E guardrails (must hold throughout)
- **NO gradients** in app/auth (already flat) and **NONE in the new landing** — the Supabase look is delivered by surfaces + 1px borders + one accent + restraint, all flat. The only `linear-gradient` permitted is a `mask-image` opacity feather on the logo strip / screenshot bottom-fade (confirm with owner; it tints nothing).
- **Mobile-responsive ≥320px, tap targets ≥40px** (owner rule 5) — preserve; the Supabase responsive `sm:/md:/lg:/xl:` ladder already supports this.
- **Do not alter** any frozen accessible name/role/placeholder listed in §0 — restyle `className` only.

---

### Key files (absolute paths)
- Tokens/theme: `C:\Users\Asus\Music\WorkSpace\projects\omr.doxaed.com\frontend\src\index.css`
- Theme default + html flag: `…\frontend\src\components\ThemeProvider.jsx`, `…\frontend\index.html`
- Fonts entry: `…\frontend\src\main.jsx`
- Components: `…\frontend\src\components\ui\{button,card,badge,input}.jsx`
- Landing (rewrite): `…\frontend\src\routes\Landing.jsx` + `…\frontend\src\routes\landing\{Hero,LandingNav,Bento,CTA,Footer,Analytics}.jsx`; delete `…\landing\{Atmosphere,Centerpiece,FlowSpine,Marquee,Micro}.jsx` + cinematic CSS (index.css 232-428)
- Auth: `…\frontend\src\components\auth\AuthLayout.jsx`, `…\frontend\src\routes\VerifyEmail.jsx`, `…\frontend\src\components\auth\GoogleButton.jsx`
- App shell (inherits): `…\frontend\src\components\AppShell.jsx`
- Frozen E2E contract (do not break): `C:\Users\Asus\Music\WorkSpace\projects\omr.doxaed.com\e2e\run.mjs`