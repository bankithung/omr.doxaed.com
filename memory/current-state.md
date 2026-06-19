# Current State

- 2026-06-19: **MAJOR redesign LOCKED — flexible orgs + nested groups + full RBAC + new plans + 4-level IA**
  (design spec `docs/superpowers/specs/2026-06-19-flexible-org-taxonomy-rbac.md`; **DESIGN ONLY, not built**).
  Owner pivoted to a Supabase-grade production product after I analysed the captured Supabase HTML in
  `prompts/uiuxreference/` (org "Projects" page + a Project page; build-ready specs extracted). **Locked
  decisions:** (D1) `Organization.type` ∈ personal/school/college/university/coaching/other seeds default
  level labels; **`ClassGroup` becomes a SELF-NESTING tree** (`parent` self-FK + `kind_label` + `order`) →
  infinite, renamable nesting (School Class→Section, Univ Dept→Program→Batch, Coaching Batch→Section, …);
  Subjects/Students(rosters)/Exams attach to any node; `folder` retired. (D2) **FULL RBAC v1:**
  `Role`(custom+system) + `RoleBinding`(scoped to a group subtree OR org-wide) + `PermissionGrant`
  (individuals) → a real `has_perm(user,org,code,group)`; `common/scope.py` rebuilt on it; today's
  `ClassAccessGrant` generalizes into a scoped Teacher binding (subject-narrowing kept). (D3) Plans re-seed
  **Free / Pro ₹1000 / Business ₹2000 / Enterprise** (default limits in spec §3). (D5) clean rebuild (tenant
  data already wiped). **4-level IA:** Organizations LIST (no sidebar) → Org workspace (Dashboard · Members ·
  Roles & Permissions · Usage · Billing · Settings) → Group workspace (recursive, type-aware: sub-groups ·
  students · subjects · exams · settings) → Exam workspace (Questions · Students · Marks · Analytics · Scan ·
  Share · Settings). **§8 production gaps folded in:** bulk CSV student import, audit log, exam lifecycle
  (Draft→Ready→Live→Closed), question bank, notifications, student profiles, class/org analytics rollups,
  guided onboarding, invoices. Build order = spec §6 (7 phases). **NEXT:** Phase 1 = org-list entry page
  (no sidebar) + create-org (name/type/plan) — awaiting go. This builds ON the org-first + class-workspace
  work already shipped below.
- 2026-06-19: **Dedicated "Generate & Print" page — first of the modals→pages conversion** (on `main`,
  `bc3dcb1`). The owner's vision is dedicated pages instead of modals for the whole OMR flow; this ships
  the first one. The class-page "Generate sheets" button now NAVIGATES to `/tests/:testId/sheets`
  (`frontend/src/routes/GenerateSheets.jsx`) instead of opening `GenerateSheetsDialog` (deleted). The
  page also adds **post-creation sheet-branding editing** — previously heading/logo were settable ONLY
  in the creation wizard; `updateTest` already supported PATCH+FormData, so the page hosts a real editor
  (edit heading, upload/replace/remove logo w/ live preview, position picker, or inherit org branding) +
  roster pick + shuffle + generate + open/print/download. New API `getTest(id)`. Branding save uses a
  FormData/JSON fork (multipart only for a NEW logo; `logo:null` only on explicit removal; inherit-on
  sends just `{brand_inherit_org:true}` so a hidden heading is never clobbered). Built with an Explore
  agent (mapped current code) + a **4-lens adversarial review Workflow** (ui-rules/wiring/edge/a11y) that
  found 10 issues (2 high, 5 med, 3 low) — ALL fixed: roster Select label-wiring + ≥40px height, logo
  group/position aria-labels, client-side 2MB logo check, success-only-when-PDF-url guard, inherit-save
  no-clobber. E2E `run.mjs` generate-sheets step updated (was dialog-based). Lint+build clean; **E2E
  Chromium/Chrome/Edge 16/16 + modeB 17/17 green.** NEXT dedicated pages: OMR edit (mostly folded into
  this page now), scan auto-detect flow, results/analytics/share; + teacher self-service.
- 2026-06-19: **RBAC — per-teacher class + subject access control COMPLETE & E2E-verified** (on `main`,
  `76afe5d`; plan `docs/superpowers/plans/2026-06-19-class-subject-access-control.md`). The first slice of
  the owner's "org → classes → subjects → members → assign access" setup vision. **Model:** `ClassAccessGrant`
  (`organizations`) links `(organization, user, class_group)` + `all_subjects` (default True) + `subjects` M2M;
  unique per (org,user,class). **API:** admin-only `/api/v1/class-grants/` CRUD (gated by `is_active_admin`;
  serializer validates class/user/subjects all in the active org). **Enforcement (all in `common/scope.py`):**
  `visibility_q` ORs in a grant predicate (`{cp}access_grants__user=user`) so a member sees a class only with a
  grant (folder-sharing path kept, additive); `can_edit_class` treats a grant as edit rights; new
  `narrowed_subject_names(request, class_group_id)` returns the allowed subject-name set (None = unrestricted)
  and the Subject viewset filters `name__in`, the Test viewset filters `Q(subject__in=names)|Q(subject="")`
  (blank tests stay visible). Admins early-return full access; solo scope unaffected. **UI:** admin-only
  "Teacher access" tab on the class page (`TestList.jsx`) — grant a member (custom `Select`), narrow via a
  chip multi-select (select none = all subjects), remove via custom confirm; `Classes.jsx` shows members with
  zero classes "Ask an admin to grant you access, or create your own." **Adversarial sweep (Task 7) FOUND+FIXED
  a real hole:** `class_group` is a writable FK and `perform_update` only gated the SOURCE class → a member
  could re-parent a Test/Subject into an ungranted class (200, should be 403). Both viewsets now gate the
  destination too (mirrors Question/Section). Also asserted: removed member's lingering grant doesn't resurrect
  access (403); generate-sheets under a non-granted class → 403. **24 access tests (incl. 4 adversarial) +
  949 total backend tests green; frontend lint+build clean; E2E Chromium/Chrome/Edge 16/16 + modeB 17/17.**
  **NEXT (owner's dedicated-pages vision, modals → pages):** generate OMR as a dedicated page (currently the
  `GenerateSheetsDialog` modal in `TestList.jsx`) → edit page (heading/logo/save/print, branding fields already
  on `Test`) → scan auto-detect → results/analytics/share; + teacher self-service (add students, own classes).
- 2026-06-18: **PRODUCT V2 in progress — Phases 0–4b merged to `main`** (plan +
  authoritative SECURITY corrections in `docs/superpowers/plans/2026-06-18-productv2-folders-papers-ux.md`).
  Owner UI rules now MANDATORY (in CLAUDE.md): no alert/native-select/default-styles/gradients;
  fully mobile-responsive; custom modals only.
  **Done + E2E-verified (Chromium/Chrome/Edge 16/16 + Mode-B 17/17):** P0 design-system primitives +
  theme; P1 responsive app shell (desktop sidebar / mobile drawer + bottom-tabs, reload-free org
  switch); P2 all list screens → DataList cards on mobile + TestList ActionMenu; **P3a per-student
  SHUFFLED QUESTION PAPER** PDF (auth-served, incl. batch endpoint — both behind auth, no /media PII);
  **P3b sheet BRANDING** (heading + logo, header re-layout that clears the roll-grid, logo DoS
  hardening, coord-invariant); **P4a inline-scan-correction backend** (per-sheet reads, whole-sheet
  regrade APPLYING corrections via shared `_persist_grading_result`, no double-charge, warped-scan
  persist, fill-ratio; student-reattach scoped — IDOR fixed); **P4b Scan & Verify UI** (whole-sheet
  results board + inline corrector: warped sheet + detected-mark overlay + whole-sheet toggle grid →
  one re-grade; drag-drop + mobile camera; enriched sheets endpoint). Auto commit-review caught +
  fixed 3 security issues this run (batch-paper /media exposure, regrade IDOR, +earlier).
  **Owner reqs captured:** scanning is already whole-page/mark-all-at-once (confirmed); configurable
  MULTIPLE-MARK rules (2/3/4 dots → disqualify/wrong/review/as-marked, teacher-set) = task #87.
  **NEXT (sequential, one agent at a time — parallel branch work caused a tangle, recovered):** 3c
  (question-paper download + branding settings + competitive section-builder UIs) · #87 multi-mark
  rules · **Phase 5 folders/sharing + admin-sees-all + subjects + onboarding** (biggest, security-
  sensitive: auth file-serving for existing pdf_file + visibility_q across ~8 views) · Phase 6 polish.
  Demo login teacher@omrflow.test / Teacher@12345. **~440+ backend tests.**
- 2026-06-18: **Mode C engine (Phase 3A+3B) merged to `main`** (`6944e24`). Competitive (NEET/UPSC):
  Section/SectionMarkingScheme models, Question.section, Test.MODE_COMPETITIVE + default_options;
  section grading — **best-K-of-attempted choose-k (shuffle-invariant)**, flat/fractional negatives
  (Decimal, single quantize), per-section subtotals, qualifying cutoffs that FLAG (never zero) the
  total; no-sections path bit-identical; retest clones sections. On-sheet section legend + §-gutter
  markers in header whitespace (NO bubble coord moved — coord-invariance test) + first-class 4/5
  options. Plan+critique in `docs/superpowers/plans/2026-06-18-phase3-modec.md`. **756 tests.**
  Competitive-test CREATION UI (section builder) deferred into Product v2.
- 2026-06-18: **PRODUCT V2 design IN PROGRESS** (owner re-scoped to the full product vision). New work:
  (1) Folders + sharing + admin-sees-everything (org content org); (2) **shuffled QUESTION PAPER** PDF
  per student when shuffle on (gap today); (3) sheet BRANDING (heading + logo placeable, proper
  spacing, scanner-safe, optional); (4) INLINE scan-error correction in the Scan UI; (5) **best-in-class
  UX/UI overhaul** — short/precise/professional onboarding, full mobile-responsive. Already-built &
  reused: org/members/roles, public /r/<slug> result page, teacher-only analytics, modes, encrypted
  PII. Design workflow (research→plan→security-critique) running; plan →
  `docs/superpowers/plans/2026-06-18-productv2-folders-papers-ux.md`.
- 2026-06-18: **Multi-mode OMR — Phase 2 (analytical profiles + report cards + PUBLIC result portal)
  COMPLETE & E2E-verified** (branch `feat/omr-modes`; not yet merged). Delivers "every test → a
  proper analytical profile" + the user's public-share-link ask.
  **2A engine** (`analytics/psychometrics.py` + TestProfile/StudentProfile + Celery `recompute_test_profile`
  hooked to batch completion): item difficulty (p-value), discrimination (27% rule), point-biserial,
  KR-20, distractor analysis by tertile, percentile/rank — GOLDEN-NUMBER tests (KR-20 0.6942,
  point-biserial 0.4704 verified by hand) + MIN_COHORT=10 + zero-variance guards.
  **2B report card** (`analytics/report_card.py`): 2-page per-student PDF — page 1 parent summary
  (score/percentile/rank/topic bars/class compare), page 2 teacher diagnostic (per-question
  shuffle-correct, distractor notes); individual + bulk endpoints; org/owner name in header.
  **2C surfacing**: Analytics "Item Analysis" tab (difficulty/discrimination/point-biserial/KR-20 +
  flags + small-cohort banner), percentile/rank + report-card download in StudentDetail, bulk
  download in Results. (Negative marking already in the wizard.)
  **2D PUBLIC result portal**: per-test "Publish results" → unguessable `/r/<slug>` (PublicResultShare
  model); no-auth lookup by roll (+ optional access-code) returns ONE result; optional leaderboard;
  name-masking; standalone public React page (no app nav). **Adversarial security review** caught +
  FIXED: a silent-no-op throttle (ScopedRateThrottle→SimpleRateThrottle, now enforces 30/min/IP),
  roll_number type-validation (list/dict→400 not 500), and a first-initial mask leak (→ fully opaque).
  Core design verified safe (per-slug isolation, IDOR, constant-time code, unpublish lifecycle).
  **VERIFIED:** full cross-browser E2E — standard 16/16 (Chromium/Chrome/Edge) + Mode-B 17/17 — now
  also covering report-card download, item-analysis, and a public-portal lookup in a fresh no-auth
  context. ~703 backend tests. Demo: `teacher@omrflow.test`/`Teacher@12345`; test 18 is published
  (a live public-portal demo link). **Next: Phase 3** (Mode C — sections/series/negative-marking;
  owner to confirm NEET-vs-UPSC fidelity + 4-vs-5 options).
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
