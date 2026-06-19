---
name: brand-accent-color
description: DoxaEd OMR brand accent is amber/gold (#F5A623), replacing Supabase green; applied app-wide
metadata:
  type: project
---

Brand accent changed from Supabase green (#3fcf8e) to **amber/gold `#F5A623`** (≈ oklch(0.78 0.15 70)) — user decision 2026-06-19. Applies to ALL surfaces (buttons, links, active nav, focus rings, badges, filled OMR bubbles), explicitly "for all, not just one section."

**Why:** green collided with grading's success-green; user wanted an accent that better matches the `#0F0F0F` gunmetal dark bg.

**How to apply:** in `frontend/src/index.css` swap `--primary` (light + dark) and the accent family (`--ring`, `--sidebar-primary`, nav-active, `--chart-1`) from green → amber/gold. Keep `--primary-foreground` near-black (`#0f0f0f`) — amber is a light hue and needs dark text for contrast. **New collision to defuse:** amber is also the grading "needs review"/warning hue — shift the grading warning/review token to a distinct **orange** (redder, e.g. ~oklch(0.70 0.18 45)) so brand-gold ≠ review-amber. Leave `--color-success` (green) and `--destructive` (red) unchanged for grading. Components must use the `primary` token, never a hardcoded hex. Related: [[brand-name]].
