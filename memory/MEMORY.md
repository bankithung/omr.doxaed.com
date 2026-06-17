# OMRFlow — Memory Index

**Status:** Phase 4 (Scanning & grading) — DONE (2026-06-17). Next: Phase 5 (Analytics & export — finishes MVP).
**Stack:** Django 5 + DRF · React (Vite, JS) + Tailwind v4 + shadcn/ui · local PostgreSQL `omrflow`.
**Repo:** Standalone git repo (own history; `backend/` + `frontend/` at root). `main` holds Phases 0–4.

## Next steps
- Phase 5 (Analytics & export — COMPLETES THE MVP = Phases 1–5) per `prompts/PRD.md` (E7):
  test-level/student-level/improvement analytics, CSV/Excel + PDF report, Recharts dashboards.
  Aggregation endpoints (scoped). See `current-state.md` for the result data model + patterns.
- Done: Phase 0 · 1 (auth) · 2 (assessments) · 3 (OMR gen) · 4 (scan/grade). 233 backend tests.

## Key facts
- DB: `omrflow`, user `postgres`, password `postgress`, localhost:5432 (no Docker). PG18.
- Python 3.13.3 (deviation from spec's 3.12). Node 22.
- UI primitives: shadcn/ui (Radix+Tailwind), JavaScript mode. Charts: Recharts.
- Roadmap: Phases 0–9, MVP = 1–5. Build one phase at a time.

## Memory index
- (none yet)
