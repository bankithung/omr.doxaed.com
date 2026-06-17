# OMRFlow — Memory Index

**Status:** Phase 1 (Accounts) — DONE (2026-06-17). Next: Phase 2 (Assessments core).
**Stack:** Django 5 + DRF · React (Vite, JS) + Tailwind v4 + shadcn/ui · local PostgreSQL `omrflow`.
**Repo:** Standalone git repo (own history; `backend/` + `frontend/` at root). `main` branch holds Phases 0–1.

## Next steps
- Phase 2 (Assessments core, solo scope) per `prompts/BUILD_ROADMAP.md` + `DATA_MODEL.md`:
  ClassGroup → Test CRUD, Question/Option authoring, MarkingScheme, retest linkage; global
  owner-scope isolation on every endpoint. Write the Phase 2 plan, then build phase-by-phase.
- Done so far: Phase 0 (foundations) + Phase 1 (auth) — 26 backend tests green.

## Key facts
- DB: `omrflow`, user `postgres`, password `postgress`, localhost:5432 (no Docker). PG18.
- Python 3.13.3 (deviation from spec's 3.12). Node 22.
- UI primitives: shadcn/ui (Radix+Tailwind), JavaScript mode. Charts: Recharts.
- Roadmap: Phases 0–9, MVP = 1–5. Build one phase at a time.

## Memory index
- (none yet)
