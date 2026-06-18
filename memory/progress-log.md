# Progress Log

- 2026-06-17 — Analyzed all 8 product specs; verified local toolchain; created
  `omrflow/phase-0` branch; wrote + committed Phase 0 design spec and implementation plan.
- 2026-06-17 — Phase 0 complete: Django+DRF backend (9 apps, custom User, owner-scope
  foundation, JWT, /api/v1/health/) on local Postgres `omrflow`; React (Vite, JS) + Tailwind v4
  + full shadcn/ui library + /style-guide; CORS+JWT seam proven; CV libs import-verified; CI added.
- 2026-06-17 — Extracted OMRFlow to its own standalone git repo (in place, fresh history).
- 2026-06-17 — Phase 1 complete (branch `phase-1`): full email/password auth — register, verify,
  login/logout (JWT blacklist), password reset (no enumeration), profile `me/`; React auth UI
  (AuthProvider, ProtectedRoute, 6 shadcn screens). Opus security review passed; 26 tests green.
- 2026-06-17 — Phase 2 complete (branch `phase-2`): assessments — ScopedModelViewSet + ClassGroup/
  Test/Question/Option/MarkingScheme CRUD, retest deep-copy, all scope-isolated; first concrete
  owner-scope CheckConstraint validated on real tables. React: classes/test-list + 3-step test
  wizard. Scope/IDOR audit caught + fixed a Critical child-scope-permission bug (Question detail
  403). 45 tests green.
- 2026-06-17 — Phase 3 complete (branch `phase-3`): roster (encrypted PII) + the OMR engine
  (geometry descriptor, deterministic shuffle/answer_key, ReportLab generator, gated generation
  endpoint + batch PDF). QR round-trip test passes; rendered sheet visually validated (clean
  fiducials/grids after a header-layout fix). 126 tests green.
- 2026-06-17 — Phase 4 complete (branch `phase-4`): OpenCV scanning/grading pipeline (align/read/
  grade/stitch) + synthetic simulator enabling a full generate→fill→scan→grade round-trip
  (perfect-score test). Scan upload (eager) + review queue endpoints + React UI. Reviewed
  grading-sound & scope-secure; 3 review-queue bugs fixed. 233 tests green.
- 2026-06-17 — 🎉 MVP COMPLETE: Phase 5 (branch `phase-5`): analytics (test-level shuffle-correct,
  student topic accuracy, retest improvement) + CSV/Excel/PDF export + Recharts dashboards. Reviewed
  analytics-correct & scope-secure (zero issues). 308 tests green. Phases 1–5 all merged to `main`.
- 2026-06-17 — Phase 6 complete (branch `phase-6`): organizations & roles — central `common/scope.py`
  refactor (solo|org context via X-Organization-Id) routed through every tenant viewset; org creation,
  invitations, member mgmt, roles, audit log. Reviewed TENANT-SECURE (no cross-org leak); fixed a
  StudentViewSet org-scope gap + removed the ?org CSRF surface. 408 tests green.
- 2026-06-17 — Phase 7 complete (branch `phase-7`): billing — Plan/Subscription, per-org plan-limit
  gates (reserve-before-work), Razorpay gateway + signature-verified webhook, billing UI. Reviewed
  BILLING-SECURE after fixing a Critical seat-gate-on-accept bypass + a TOCTOU race. 496 tests green.
  Live payments pending the user's Razorpay keys.
- 2026-06-18 — Phase 8 complete (branch `phase-8`): production-grade hardening — env-driven prod
  security (check --deploy clean), django-axes lockout, no-enumeration register, Celery async (eager
  in dev) + DB indexes, frontend code-splitting (940→307 kB) + a11y + clean lint, image-upload API,
  deployment config + DEPLOYMENT.md + SECURITY-CHECKLIST.md. 535 tests green. Verified PRODUCTION-READY.
- 2026-06-18 — Gap-closure + full cross-browser E2E (branch `gap-closure` → `main`). Roadmap-vs-code
  audit: core loop fully wired. Closed gaps: removed non-existent "viewer" role; added GET
  /billing/plans (Billing shows real seeded limits); wired student-detail drill-down + audit-log UIs;
  documented intentional free-org-1-seat gating. Built a Playwright suite (`e2e/`) driving the WHOLE
  loop unmocked (synthetic scans of real sheets via the simulator; email verify-token regenerated) —
  **PASSED 14/14 in Chromium + Chrome + Edge.** E2E caught + fixed 2 real runtime bugs (Results.jsx
  flat-vs-nested serializer fields; avg-score NaN from Decimal-as-string). 540 tests green.
- 2026-06-18 — Front door + generation fix (branch `feat/landing-home` → `main`). User manual-testing
  found: (a) `/` was a dev API-health stub + Style Guide in the nav → built a real Landing (logged-out)
  + Dashboard (logged-in) + auth-aware RootRoute; post-login → /dashboard; nav cleaned (dev routes
  kept). Done via a 6-agent Workflow (understand→design→build→review = APPROVE); fixed a dashboard
  email-overflow. (b) Re-generating sheets 500'd on duplicate deterministic sheet_code → made
  generation idempotent (update_or_create on (test,student), pk preserved) + regression test.
  Re-verified full loop + new front door across Chromium/Chrome/Edge (15/15). Demo acct
  teacher@omrflow.test / Teacher@12345.
