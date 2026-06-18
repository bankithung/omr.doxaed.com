# OMRFlow — Memory Index

**Status (2026-06-19):** **DoxaEd OMR** (renamed from OMRFlow). On `main`: a **cinematic animated landing** (dark, gradients/glow, pinned scroll-jacked 4-act centerpiece, framer-motion, landing-only) + a **Supabase-grade app overhaul** (flat oklch tokens light+**dark mode**, two-level sidebar AppShell v2, ⌘K command palette, all pages migrated to Card/DataTable/PageHeader/Settings layout, branded auth pages, **env-driven Google Sign-In** [set `VITE_GOOGLE_CLIENT_ID`+`GOOGLE_CLIENT_ID`], Terms/Privacy pages). 924 backend tests; E2E Chromium/Chrome/Edge 16/16 + modeB 17/17. Design spec scratch: `appdesign-spec-tmp.md` (gitignored). **App stays FLAT (no gradients); gradients only on `.landing-cinematic`.** Demo login teacher@omrflow.test / Teacher@12345.
<br>**(earlier)** Phases 0–8 + multi-mode + **PRODUCT V2 Phases 0–6 COMPLETE** (design system, responsive shell, mobile lists, shuffled question paper, sheet branding + settings UI + paper download, inline scan-correction + Scan-&-Verify UI, #87 configurable multi-mark rules, **Phase 5** folders+sharing+admin-override+subjects+onboarding [adversarially audited: 1 HIGH found+fixed], **Phase 6** skeletons/empty/error states + AppShell refetch dedup + mobile sweep + breadcrumbs + test-progress rail). Owner decisions: [phase5-visibility-decisions](phase5-visibility-decisions.md) (existing data org-visible; admins FULL edit/delete). Plan: `docs/superpowers/plans/2026-06-18-productv2-folders-papers-ux.md`. **UI rules mandatory (CLAUDE.md): no alert/native-select/default-styles/gradients; mobile-responsive; custom modals.** **917 backend tests; E2E Chromium/Chrome/Edge 16/16 + modeB 17/17 green; `check` clean.** Dev throttle relaxed via local `.env` (THROTTLE_USER/ANON; prod keeps 120/30-min defaults). Deferred/nice-to-have: AppShell still ~13 org+13 me calls/run (down from 24/22 — could cache harder); onboarding click-path not E2E-covered (bypassed by design); rail Build/Generate stages need backend class_group on the analytics test block to deep-link.
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
- [brand-name](brand-name.md) — product is "DoxaEd OMR" (was OMRFlow); user-facing strings only, keep internal `omrflow` ids
- [phase5-visibility-decisions](phase5-visibility-decisions.md) — owner-approved folders/sharing visibility + admin-override choices (gate Phase 5B/5C)
