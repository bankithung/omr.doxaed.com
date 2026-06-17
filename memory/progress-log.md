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
