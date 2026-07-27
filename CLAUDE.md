# OMRFlow — Project Router

Code project. Build strictly phase-by-phase per `prompts/BUILD_ROADMAP.md` (Phases 0–9;
MVP = 1–5). One phase at a time; do not start a phase before the prior is "done".

## Source of truth
- `prompts/` — 8 product specs (PRD, TECHNICAL_ARCHITECTURE, DATA_MODEL, OMR_ENGINE_SPEC,
  DESIGN_SYSTEM, AGENT_PROMPT, BUILD_ROADMAP, README). Treat as authoritative; flag conflicts.
- `docs/superpowers/specs/` and `docs/superpowers/plans/` — per-phase design + implementation.

## Stack & rules
- Backend: Django 5 + DRF, pure JSON API under `/api/v1`, all business logic server-side.
- Frontend: React (Vite, JavaScript) + Tailwind v4 + shadcn/ui; custom components only.
  **NON-NEGOTIABLE UI RULES (owner):** (1) NO `alert()`/`confirm()`/`prompt()` — always a custom-styled
  modal. (2) NO native/default dropdowns or `<select>` — custom-styled Select/menu only. (3) NO default/
  unstyled elements — everything explicitly custom-styled. (4) NO gradients anywhere — flat solid colors.
  (5) EVERY page + all content fully mobile-responsive (320→desktop), tap targets ≥40px.
  (6) NO dashes in any user-facing text: no em dash, no en dash, no hyphen used as punctuation.
  Use a comma or a full stop instead. Sub text stays short and precise (aim ≤ 60 chars).
  (7) EVERY page body is 90% of the available width, capped at 1600px (`PageShell`). Do not add
  inner `max-w-*` caps to page content; they are reserved for overlays and text truncation.
- Design system: the theme is ported from `bankithung/fet.doxaed.com` (Doxaed Timetables) so both
  products read as one family. Canvas #F4F3EF, ground #F7F6F2, tray #ECEBE7, ink #130537,
  indigo #3F20FB (primary + interactive tint), lavender #DCB3F2, danger #B42318, success #1B7F4F.
  Radius 5px everywhere, Inter, body 13px, flat surfaces with hairline borders. Light theme only.
  All of it lives in `frontend/src/index.css`; change a token there, never a hard-coded colour.

## Git
- ALWAYS develop and push to `main`. Do not open feature branches or pull requests unless
  explicitly asked.
- DB: local PostgreSQL `omrflow` (user `postgres`, password `postgress`, localhost:5432). No Docker.
- Owner-scope isolation is global: every tenant row is owned by user XOR organization.
- OMR grading uses each sheet's stored answer_key; low-confidence reads → review queue, never guessed.
- Secrets via env vars only. Tests required for grading, scope isolation, plan limits.

## Onboarding
Read this file → `memory/MEMORY.md` → `memory/current-state.md` → the active phase plan.
