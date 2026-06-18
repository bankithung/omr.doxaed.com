# OMRFlow — Memory Index

**Status:** Webapp production-ready (Phases 0–8 on `main`). NOW building **multi-mode OMR** (`feat/omr-modes`): 6 modes + advanced features per `docs/superpowers/specs/2026-06-18-omr-modes-and-advanced-features.md` (7-phase roadmap). **Phase 1 (mode scaffold + Mode B pre-bubbled roll) DONE & E2E-verified, not yet merged.** Next: Phase 2 (analytics core). Mobile app still pending.
**Stack:** Django 5 + DRF · React (Vite, JS) + Tailwind v4 + shadcn/ui · local PostgreSQL `omrflow`.
**Repo:** Standalone git repo (own history; `backend/` + `frontend/` at root). `main` holds Phases 0–8 + gap-closure. **540 tests**, lint clean. Cross-browser E2E suite in `e2e/` (`node run.mjs`).
⚠️ Before launch: real Razorpay keys + payments review; TLS + prod env; Redis+Celery worker; audits/backups/monitoring. See `docs/DEPLOYMENT.md` + `docs/SECURITY-CHECKLIST.md`.

## Next steps
- The full MVP loop works: create test → generate OMR sheets → scan & auto-grade → analytics/export → retest.
- Post-MVP per `prompts/BUILD_ROADMAP.md`: Phase 6 (Organizations & roles), 7 (Razorpay billing),
  8 (hardening — Celery/Redis async, OWASP, calibration, code-splitting), 9 (mobile app).
  See `current-state.md` for the architecture patterns + deferred follow-ups.
- Done: P0 · P1 (auth) · P2 (assessments) · P3 (OMR gen) · P4 (scan/grade) · P5 (analytics). 308 tests.

## Key facts
- DB: `omrflow`, user `postgres`, password `postgress`, localhost:5432 (no Docker). PG18.
- Python 3.13.3 (deviation from spec's 3.12). Node 22.
- UI primitives: shadcn/ui (Radix+Tailwind), JavaScript mode. Charts: Recharts.
- Roadmap: Phases 0–9, MVP = 1–5. Build one phase at a time.

## Memory index
- (none yet)
