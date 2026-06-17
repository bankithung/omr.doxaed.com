# OMRFlow — Memory Index

**Status:** Phase 2 (Assessments) — DONE (2026-06-17). Next: Phase 3 (Roster & OMR generation).
**Stack:** Django 5 + DRF · React (Vite, JS) + Tailwind v4 + shadcn/ui · local PostgreSQL `omrflow`.
**Repo:** Standalone git repo (own history; `backend/` + `frontend/` at root). `main` holds Phases 0–2.

## Next steps
- Phase 3 (Roster & OMR generation) per `prompts/BUILD_ROADMAP.md` + `OMR_ENGINE_SPEC.md`: Roster +
  Student models, ReportLab OMR PDF generation (QR/fiducials/roll-grid/answer-grid), per-student
  shuffle + answer_key + template_descriptor, multi-page + page_map, batch PDF, free-tier gates.
  Write the Phase 3 plan, then build. See `current-state.md` for the child-scope permission pattern.
- Done: Phase 0 (foundations) · Phase 1 (auth, 26 tests) · Phase 2 (assessments, 45 tests).

## Key facts
- DB: `omrflow`, user `postgres`, password `postgress`, localhost:5432 (no Docker). PG18.
- Python 3.13.3 (deviation from spec's 3.12). Node 22.
- UI primitives: shadcn/ui (Radix+Tailwind), JavaScript mode. Charts: Recharts.
- Roadmap: Phases 0–9, MVP = 1–5. Build one phase at a time.

## Memory index
- (none yet)
