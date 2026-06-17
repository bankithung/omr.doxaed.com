# OMRFlow — Project Router

Code project. Build strictly phase-by-phase per `prompts/BUILD_ROADMAP.md` (Phases 0–9;
MVP = 1–5). One phase at a time; do not start a phase before the prior is "done".

## Source of truth
- `prompts/` — 8 product specs (PRD, TECHNICAL_ARCHITECTURE, DATA_MODEL, OMR_ENGINE_SPEC,
  DESIGN_SYSTEM, AGENT_PROMPT, BUILD_ROADMAP, README). Treat as authoritative; flag conflicts.
- `docs/superpowers/specs/` and `docs/superpowers/plans/` — per-phase design + implementation.

## Stack & rules
- Backend: Django 5 + DRF, pure JSON API under `/api/v1`, all business logic server-side.
- Frontend: React (Vite, JavaScript) + Tailwind v4 + shadcn/ui; custom components only —
  NO native `<select>`/`alert()`/`confirm()`/`prompt()`. Responsive 320→desktop.
- DB: local PostgreSQL `omrflow` (user `postgres`, password `postgress`, localhost:5432). No Docker.
- Owner-scope isolation is global: every tenant row is owned by user XOR organization.
- OMR grading uses each sheet's stored answer_key; low-confidence reads → review queue, never guessed.
- Secrets via env vars only. Tests required for grading, scope isolation, plan limits.

## Onboarding
Read this file → `memory/MEMORY.md` → `memory/current-state.md` → the active phase plan.
