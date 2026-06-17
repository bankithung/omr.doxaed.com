# OMRFlow — Memory Index

**Status:** Phase 3 (OMR generation) — DONE (2026-06-17). Next: Phase 4 (Scanning & grading).
**Stack:** Django 5 + DRF · React (Vite, JS) + Tailwind v4 + shadcn/ui · local PostgreSQL `omrflow`.
**Repo:** Standalone git repo (own history; `backend/` + `frontend/` at root). `main` holds Phases 0–3.

## Next steps
- Phase 4 (Scanning & grading — HARDEST) per `prompts/OMR_ENGINE_SPEC.md` + `BUILD_ROADMAP.md`:
  ScanBatch/ScanJob, async OpenCV pipeline (QR→fiducials→warp→roll dots→answer fill-ratio→stitch→
  grade vs the per-sheet `answer_key`)→StudentResult/QuestionResponse, manual review queue, progress.
  See `current-state.md` → "generator↔scanner contract" (the descriptor) and build a fixture set early.
- Done: Phase 0 · Phase 1 (auth, 26 tests) · Phase 2 (assessments, 45 tests) · Phase 3 (OMR gen, 126 tests).

## Key facts
- DB: `omrflow`, user `postgres`, password `postgress`, localhost:5432 (no Docker). PG18.
- Python 3.13.3 (deviation from spec's 3.12). Node 22.
- UI primitives: shadcn/ui (Radix+Tailwind), JavaScript mode. Charts: Recharts.
- Roadmap: Phases 0–9, MVP = 1–5. Build one phase at a time.

## Memory index
- (none yet)
