# OMRFlow — Memory Index

**Status:** On `main`: Phases 0–8 + multi-mode (Mode B pre-bubbled roll, Mode C competitive engine, analytics profiles, report cards, public result portal) + **PRODUCT V2 Phases 0–4b** (design system, responsive shell, mobile lists, shuffled question paper, sheet branding, inline scan-correction + Scan-&-Verify UI). Plan: `docs/superpowers/plans/2026-06-18-productv2-folders-papers-ux.md`. **UI rules mandatory (CLAUDE.md): no alert/native-select/default-styles/gradients; mobile-responsive; custom modals.** Next (sequential): 3c UIs · #87 multi-mark rules · **Phase 5 folders/sharing/admin** · Phase 6 polish. ~440+ tests, E2E Chromium/Chrome/Edge green.
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
