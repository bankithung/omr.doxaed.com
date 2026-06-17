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
