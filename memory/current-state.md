# Current State

- 2026-06-18: **Multi-mode OMR — Phase 1 (mode scaffold + Mode B pre-bubbled roll) COMPLETE**
  (branch `feat/omr-modes`). New product direction: multiple test-creation MODES + advanced
  differentiators, designed in `docs/superpowers/specs/2026-06-18-omr-modes-and-advanced-features.md`
  (6 modes — Standard, Roster pre-bubbled roll, Competitive NEET/UPSC, Mixed-types JEE/GATE,
  Data-capture, Survey — + a 7-phase roadmap; critique verdict SOLID).
  **Phase 1 shipped (1A+1B+1C):** `Test.mode` (default `standard` = zero change) + `template_spec`;
  `build_template(roll_kind=...)` + descriptor `roll_grid.kind/prefilled`; generator draws SOLID
  pre-bubbled roll discs (proven scannable on the REAL fitz→Otsu path, fill ratio 1.0, +0.55 margin
  over FILL_HIGH); `OmrSheet.roll_kind/roll_value` (roll zero-padded right-aligned to grid width);
  **scan identity** — `_parse_test_id_from_sheet_code` cross-checks the QR's test_id vs the batch →
  `test_mismatch` (never grades against the wrong test); **verify-only roll reconciliation** —
  prebubbled roll read & symmetric-zfill-normalized vs `student.roll_number` → `roll_mismatch`
  review flag (identity ALWAYS from QR; short rolls never false-fire); widened `ReviewItem.reason`
  20→32 + `test_mismatch`/`roll_mismatch` reasons; TestWizard mode picker + writable `mode` API +
  friendly review labels. **VERIFIED:** full E2E across Chromium/Chrome/Edge (standard 15/15 each)
  + a Mode-B journey (16/16: pre-bubbled roll → auto-identify → graded → **tampered roll flags
  roll_mismatch**). Backend suite green. NOT yet merged to `main` (pending final suite + merge).
  **Next: Phase 2** (analytics core — item analysis/percentile/report card), then Phase 3+ (Mode C
  competitive: sections/series/negative-marking). Owner decisions for Mode C deferred (NEET-vs-UPSC
  fidelity, 4-vs-5 options) — building generic; will confirm at Phase 3.
- 2026-06-18: **Real front door + idempotent generation fix** (branch `feat/landing-home` → `main`).
  Manual user testing exposed two issues the automated loop missed. (1) The root route `/` rendered a
  dev **API-health stub** and the nav exposed the internal Style Guide — replaced with a real
  **Landing** page (logged-out marketing: hero, feature grid, how-it-works, CTAs) + a **Dashboard**
  home (logged-in: greeting, quick actions, stat cards, recent classes/rosters via existing APIs).
  `auth/RootRoute.jsx` gates `/` on `useAuth().loading` (Dashboard if `user`, else Landing — no flash);
  post-login now goes to `/dashboard`; nav brand → `/`, Style-Guide link removed (route kept for devs).
  Built via a 6-agent Workflow (understand→design→build→review, verdict APPROVE); fixed a StatCard
  email-overflow + added skeleton loaders. (2) **`fix(omr)`: re-generating sheets for a test that
  already had them 500'd** (duplicate deterministic `sheet_code`) — switched the per-student
  `create()` to `update_or_create((test, student))`, so regeneration is idempotent and preserves the
  row pk (results stay valid); added a regression test. Re-verified the WHOLE loop + the new front
  door across **Chromium/Chrome/Edge — 15/15 steps each** (E2E now also asserts the landing page +
  the "Welcome back" dashboard). Demo login for the running app: `teacher@omrflow.test` / `Teacher@12345`.
- 2026-06-18: **✅ PRODUCTION-READY — gaps closed + full cross-browser E2E PASSED** (branch
  `gap-closure` → merged to `main`). A roadmap-vs-code gap audit found the core loop fully wired;
  closed the real gaps: removed a non-existent "viewer" role (silent-failure), added a real
  `GET /billing/plans/` endpoint (Billing UI now shows truthful seeded limits, not stale hard-codes),
  wired the built-but-unreachable **student-detail** drill-down + **audit-log** UIs. **540 backend
  tests.** Then ran a Playwright E2E driving the ENTIRE loop (register → verify → login → class →
  test(MCQs) → roster+students → generate sheets → upload synthetic scans → auto-grade → results →
  student drill-down → analytics → export CSV/Excel/PDF) in **all 3 available browsers (Chromium,
  Chrome, Edge) — 14/14 steps each, unmocked CV/QR/grade pipeline**. The E2E surfaced + fixed two
  real runtime bugs unit tests missed: Results.jsx read nested `student.*` fields but the API is flat
  (`student_roll`/`student_name`/`student` FK id) → roll/name cols + the Detail link broke; and
  avg-score did string-concat on DRF Decimal-as-string → `NaN` (now `Number()`-coerced). Grading
  verified correct (perturbed sheet scored 4/5, rest 5/5; analytics avg 4.8). Harness lives in `e2e/`
  (`run.mjs` + `django_helper.py`, see `e2e/README.md`). Screenshots/exports captured as evidence.
- 2026-06-18: **Phase 8 (Hardening — production-grade) complete** (branch `phase-8` → merged to `main`).
  Env-driven production security (secure cookies/HSTS/SSL/headers, WhiteNoise static, a fail-closed
  prod-config guard) — `check --deploy` is CLEAN under prod env. Auth hardening: django-axes login
  lockout, registration no-enumeration, verify-email throttle. Async scanning via Celery (eager in
  dev, broker-ready for prod). DB indexes on hot paths. Frontend route code-splitting (940→307 kB
  main) + a11y pass (0 a11y errors) + **production-clean lint (0 errors)**. Question image-upload
  API. Deployment: `gunicorn.conf.py`, `Procfile`, `backend/.env.prod.example`, `docs/DEPLOYMENT.md`,
  `docs/SECURITY-CHECKLIST.md` (OWASP). **535 backend tests.** Verified PRODUCTION-READY pending the
  external steps below.
  **Must-do before LAUNCH (external/ops):** real Razorpay keys + a payments security review; TLS +
  the prod env vars; a Redis broker + a Celery worker (set `CELERY_TASK_ALWAYS_EAGER=False`);
  `pip-audit`/`npm audit`; DB backups; monitoring (Sentry); decide scan-metering granularity.
- 2026-06-17: **Phase 7 (Subscription & billing) complete** (branch `phase-7` → merged to `main`).
  `billing` app: Plan (Free/Team ₹500/Business ₹1000/Enterprise, seeded) + per-org Subscription;
  `limits.py` resolves the org's plan and enforces SERVER-SIDE per-org gates (seat / generations-day
  / students-per-gen / monthly-scan caps, reserve-before-work to close TOCTOU). Razorpay via
  `billing/gateway.py` (create_subscription + HMAC-SHA256 **signature-verified webhook**, idempotent).
  Free org = 1 seat (admin); adding staff / higher caps needs a paid sub. Reviewed BILLING-SECURE
  after fixing a Critical seat-gate-on-accept bypass. **496 backend tests.** React billing UI (plan +
  usage bars, tier cards, subscribe→Razorpay checkout). ⚠️ LIVE PAYMENTS need the user's Razorpay
  keys (`RAZORPAY_KEY_ID/_KEY_SECRET/_WEBHOOK_SECRET` in `backend/.env`) + a payments security review.
- 2026-06-17: **Phase 6 (Organizations & roles) complete** (branch `phase-6` → merged to `main`).
  Multi-tenancy: a request acts in SOLO scope by default or ORG scope via the `X-Organization-Id`
  header (active member only); `common/scope.py` (`scope_filter`/`scope_kwargs`/`get_active_org`)
  centralizes it and EVERY tenant viewset routes through it (all prior solo tests still pass). Org
  data is org-owned + shared among members. Org creation (auto-admin), invitations (email→accept),
  member management + roles (admin/member, last-admin protection), audit log. Reviewed
  TENANT-SECURE & ROLES-CORRECT (live multi-actor probe; no cross-org leak). **408 backend tests.**
  React: org switcher (sets the header) + create/members/invite/accept UI.
- 2026-06-17: **🎉 MVP COMPLETE (Phases 1–5).** Phase 5 (Analytics & export) merged to `main`.
  A teacher can now run the entire loop end-to-end: **create class/test/MCQs → generate
  personalized OMR sheets → print → scan & auto-grade → read analytics → export / retest & compare.**
  Phase 5 adds: test-level analytics (distribution, average/median, toppers, hardest questions,
  per-option choice distribution — all shuffle-correct), student-level (topic accuracy), retest
  improvement (deltas + class trend), CSV/Excel/PDF export, Recharts dashboards. Reviewed
  ANALYTICS-CORRECT & SCOPE-SECURE. **308 backend tests green.**
- **Done (MVP = Phases 1–5, all merged to `main`):**
  - P0 Foundations (decoupled Django+DRF / React skeleton, owner-scope, local Postgres).
  - P1 Accounts (register/verify/login/logout/reset/profile; JWT; reviewed).
  - P2 Assessments (Class/Test/Question/Option/Marking/retest; scope-isolated).
  - P3 OMR generation (geometry descriptor, shuffle, ReportLab sheets w/ QR/fiducials/roll/answer
    grid; gated generation + batch PDF; visually validated).
  - P4 Scanning & grading (OpenCV pipeline align/read/grade/stitch; synthetic round-trip;
    review queue; grading-sound & scope-secure).
  - P5 Analytics & export.
- **Next (post-MVP, per `prompts/BUILD_ROADMAP.md`):**
  - **Phase 6** Organizations & roles (org creation, invitations, membership, admin vs member,
    org-scope isolation — extend `IsInScope` with the org-membership path, audit log).
  - **Phase 7** Subscription & billing (Razorpay plans/subscriptions/webhooks; seat + scan caps).
  - **Phase 8** Hardening (OWASP pass, Celery+Redis async scanning, threshold calibration vs real
    scans, perf/indexes, a11y, code-splitting; + the deferred items below).
  - **Phase 9** Mobile app (React Native/Flutter against the existing API).

## Architecture patterns (recap — FOLLOW in Phases 6+)
- Direct `OwnerScopedModel` → `ScopedModelViewSet` (IsInScope). Child-scoped (under a Test) →
  `IsAuthenticated` + queryset filtered through the parent's scope.
- PII via `common.encryption.EncryptedTextField`. Free-tier gates server-side.
- Per-sheet shuffle: grade + analytics map via the OmrSheet's `question_order`/`option_order`/`answer_key`.

## Deferred follow-ups (for Phase 6/8)
- **Phase 6:** extend `IsInScope.has_object_permission` with the org-membership path + `super()`.
- **Phase 7 billing remaining (needs user / business):** add real Razorpay keys to go live + a
  payments security review; decide scan metering granularity (currently per-upload-batch, spec implies
  per-sheet); annual billing (2 months free) UI; proration/dunning/invoices. (Per-org quotas + the
  org-creation→sub model are DONE; org creation is open with a free-plan 1-seat gate.)
- **Phase 8 hardening:** Celery+Redis async scanning (dev is eager); FILL_HIGH/LOW + fiducial
  calibration vs real photos; cropped review-region images; register-email enumeration; verify-email
  throttle; account lockout (django-axes); frontend code-splitting (bundle ~918 kB).
- **Leftovers:** question/option image upload API (models have ImageField, serializers omit);
  unused User.first_name/last_name; hand-authored form.jsx still unused; partial-marking net-zero
  counts as wrong (documented).

## Resolved
- P1 AllowAny · P2 child-scope 403 · P3 sheet header overlaps · P4 review-queue (needs_review/dedup/no_qr).
