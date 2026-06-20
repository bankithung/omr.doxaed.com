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
- 2026-06-18 — Mode C engine (branch `feat/modec-phase3` → `main`): sections + per-section grading
  (best-K choose-k shuffle-invariant, flat/fractional negatives, cutoffs flag-not-zero, no-sections
  bit-identical, retest clones sections) + on-sheet section headers (coord-invariant) + 4/5 options.
  Design workflow caught 3 issues pre-build (choose-k fairness, header geometry, retest). 756 tests.
  Competitive CREATION UI deferred into Product v2. Then owner re-scoped → PRODUCT V2 (folders/sharing/
  admin-visibility, shuffled question paper, sheet branding/logo, inline scan correction, UX/onboarding/
  mobile overhaul) — design workflow (NEEDS_REVISION, security corrections folded in).
- 2026-06-18 — PRODUCT V2 Phases 0–4b merged to `main`: P0 design-system + theme; P1 responsive shell
  (sidebar/drawer/bottom-tabs, reload-free org switch); P2 mobile list cards (DataList) + TestList
  ActionMenu; P3a per-student shuffled question paper PDF (auth-served + batch); P3b sheet branding
  (heading+logo, header re-layout clears roll-grid, logo DoS guard, coord-invariant); P4a inline-scan
  backend (per-sheet reads, whole-sheet regrade applying corrections, warped persist, fill-ratio,
  scoped reattach); P4b Scan & Verify UI (board + warped-overlay corrector, whole-sheet, camera). Owner
  UI rules locked in CLAUDE.md. Auto commit-review caught+fixed batch-paper /media exposure + regrade
  IDOR. Parallel-agent branch tangle recovered (now sequential). Each phase E2E-verified across 3
  browsers. Next: 3c UIs · #87 multi-mark rules · Phase 5 folders/sharing · Phase 6 polish.
- 2026-06-18 — PRODUCT V2 Phase 3c + #87 merged to `main`. **3c** (worktree, 8408f9d→merged):
  TestSerializer branding fields writable + org-branding endpoint (admin-only) + wizard branding
  section + org branding card + "Download question papers" (authed blob). Follow-up fix (654f60f):
  multipart test creation parsed marking_scheme JSON string + rebuilt as plain dict (DRF html-input
  flattening) so branded-with-logo tests persist instead of 400 (+regression test). **#87 configurable
  multi-mark rules** (ee5f787): MarkingScheme/SectionMarkingScheme.multi_mark_policy ∈ {review(default,
  back-compat), disqualify(void/no-penalty), wrong(negative), correct_if_all(lenient)}; grade_sheet owns
  the authoritative overmark decision (len(marked)>len(correct)) so review routing follows the GRADE
  (fixes false-positive review on legit multiple-correct); double_mark review-item creation moved from
  per-page process_scan_job → policy-aware _persist_grading_result; StudentResult.disqualified_count;
  custom radio-card policy picker in TestWizard. 470 backend tests; E2E Chromium/Chrome/Edge 16/16 +
  modeB 17/17 green after each. Next: Phase 5 (folders/sharing/admin/subjects/onboarding) · Phase 6 polish.
- 2026-06-18 — PRODUCT V2 **Phase 5 BACKEND** merged to `main` (9cc1719). 5A (folders app: Folder
  OwnerScoped + FolderShare + ClassGroup.folder + Subject; 50 tests). 5B+5C (b50e744): `visibility_q`
  union in common/scope.py (creator|member-share|org-share|loose=creator+admin; admin FULL access bounded
  to active org; solo=Q() no-op) threaded into EVERY query site (+`.distinct()`) and reused by
  IsInScope.has_object_permission (`view.get_queryset().filter(pk).exists()` → no list/object drift);
  FolderViewSet/FolderShareViewSet (cross-org grantee→400), SubjectViewSet, ClassGroup `?folder=`+writable
  folder; `can_edit_class` gates ALL writes (VIEW-only→403); grandfather migration (per-org "General"
  folder + org-wide VIEW shares so existing data stays org-visible). **Adversarial red-team workflow**
  (7 vectors): 6 clean, 1 HIGH found+fixed (0f2968e: Question/Section/Student perform_update gated only
  SOURCE parent → a member could re-parent a child into a VIEW-only same-org test/roster via writable FK;
  now gates source+dest, +2 regression tests). 917 backend tests; E2E Chromium/Chrome/Edge 16/16 + modeB
  17/17. NEXT: Phase 5D/5E frontend (folders UI + sharing + subjects + onboarding) → Phase 6 polish.
- 2026-06-18 — PRODUCT V2 **Phases 5D/5E + 6 COMPLETE** → `main` (b0a04bb). 5D folders/sharing/subjects
  UI (7f30f8e: /folders + /folders/:id, custom share modal member/org VIEW/EDIT, Folders nav, optional
  folder picker on class create, per-class Subjects + wizard subject Select w/ free-text fallback). 5E
  onboarding (08aa47e: /onboarding 5-step wizard, localStorage-gated redirect, run.mjs addInitScript
  bypass, "Workspace ready" banner). 6A (fb54b8b: content-skeletons + standardized EmptyState +
  ErrorState-with-retry across ~17 routes; AppShell org-list+/auth/me dedup measured 24/22→13/13 per run).
  6B (50ddbf3: 320px mobile sweep, Analytics scrollable tabs/legible charts/2-up StatCards, TestWizard
  compact stepper + sticky footer, TestProgressRail replacing the 6-button row [same routes], breadcrumbs,
  PublicResult touch). E2E artifact resolved honestly: heaviest modeB flow burst past 120/min UserRate
  throttle at machine speed → made user/anon rates env-overridable (1310a4d; prod defaults intact, local
  .env relaxes). NO backend mojibake existed (repo scan = 0). 917 backend tests; E2E Chromium/Chrome/Edge
  16/16 + modeB 17/17; check clean. **Product v2 (Phases 0–6) DONE end-to-end.**
- 2026-06-18 — CINEMATIC LANDING rebuild → `main` (f69169d). Owner found the first (flat reveal-on-scroll)
  landing "lame/AI-slop"; wanted agency-grade "wow" + scroll-up animations + asked to study other sites.
  Ran a 6-agent research workflow (best-in-class landing motion techniques) → build-ready storyboard.
  Owner decisions: gradients/glow ALLOWED **on the landing route only** (app stays flat, CLAUDE.md rule
  intact elsewhere); north-star = **Apple cinematic pinned scrollytelling**. Built `frontend/src/routes/
  landing/*` (motion/tokens.js, Hero, Centerpiece, Bento, Marquee, CTA, Footer, Micro, LandingNav) +
  rewrote Landing.jsx as a self-contained DARK canvas (`.landing-cinematic`, explicit colors, no theme
  bleed). Centerpiece = ONE pinned `h-[450vh]` section, sticky stage, one useSpring-smoothed scrollYProgress,
  4 crossfaded acts (assemble → deal out 8 unique shuffled sheets → scan-wipe → analytics), bidirectional.
  Added **framer-motion 12** (lazy in Landing chunk; +`.npmrc` legacy-peer-deps for eslint10). **Critical fix:**
  wrapper `overflow-x-hidden`→`overflow-x-clip` (hidden forced overflow-y:auto → scroll container → broke
  position:sticky → blank centerpiece). Screenshot-verified all acts at scroll depths; E2E 16/16+17 (hero h1
  keeps "Grade a stack of bubble sheets"). Iterating on refinement next.
- 2026-06-19 — **SUPABASE-GRADE APP OVERHAUL + DoxaEd OMR rebrand COMPLETE → `main`**. Owner wanted the
  logged-in app to feel like Supabase (multi-level sidebar) + all pages premium + login/signup/forgot/reset
  + Google sign-in + Terms/Privacy + rebrand. Ran a 6-agent research workflow → build-ready spec
  (`appdesign-spec-tmp.md`, gitignored scratch at repo root). Executed in phases (each E2E-verified+merged):
  **P1** (1c74efe) flat oklch tokens light+dark + AppShell v2 (icon rail + route-driven contextual secondary
  panel + TopBar breadcrumb/⌘K/OrgSwitcher/AccountMenu/ThemeToggle + test/org-scoped panels) + cmdk command
  palette + Card/Avatar/DataTable/skeletons + dark mode (next-themes); fixed 2 dead nav links. **P2a/P2b**
  (0f9e739, 7c9421c) migrated ALL pages to PageShell/PageHeader/DataTable/Card/status-tokens; horizontal
  TestProgressRails removed (test-scoped panel replaces); Profile→full Settings layout. **P3** (e10d8b6)
  branded split AuthLayout (Login/Register/Forgot/Reset) + **env-driven Google Sign-In** (GIS frontend +
  POST /auth/google/ verifying ID token, 503 when unset; needs `VITE_GOOGLE_CLIENT_ID` + `GOOGLE_CLIENT_ID`
  = the Google Cloud OAuth Web Client ID; secret NOT needed) + **Terms (/terms) + Privacy (/privacy)** pages
  (template, needs legal review). **P4 rebrand** (bcd8fa9) OMRFlow→DoxaEd OMR all user-facing (nav/onboarding/
  emails/report-card+question-paper PDFs/from-email); kept internal `omrflow` db + `@omrflow.test` fixtures.
  **Polish** edge pages (onboarding/verify/accept). Parallel-agent tangle happened (worktree isolation flag
  DIDN'T take — both ran on shared tree) but self-resolved into disjoint branches; LESSON: run agents
  SEQUENTIALLY. 924 backend tests; E2E Chromium/Chrome/Edge 16/16 + modeB 17/17; build/lint clean; no app
  gradients (landing-only). Screenshot-verified shell+pages+auth light+dark = genuinely premium.
- 2026-06-18 — Multi-mode OMR Phase 2 (branch `feat/omr-modes`): analytical profiles + report cards
  + PUBLIC result portal. 2A psychometrics engine (difficulty/discrimination/point-biserial/KR-20/
  distractors/percentile, golden-number tested, min-cohort+zero-variance guards, Celery-populated).
  2B 2-page report card PDF (parent summary + teacher diagnostic, individual+bulk). 2C item-analysis
  tab + percentile/rank + report-card downloads. 2D public /r/<slug> portal (publish toggle, no-auth
  roll lookup, optional access-code + leaderboard, name masking). Adversarial security review caught+
  fixed a silent-no-op throttle, roll_number type-validation, and a mask initial-leak. Full E2E
  Chromium/Chrome/Edge (standard 16/16 + Mode-B 17/17) incl. report-card download + public lookup.
  ~703 tests. Next: Phase 3 (Mode C competitive).
- 2026-06-18 — Multi-mode OMR initiative (branch `feat/omr-modes`). Deep research+design workflow →
  spec `docs/superpowers/specs/2026-06-18-omr-modes-and-advanced-features.md` (6 modes, 7-phase
  roadmap, critique SOLID). **Phase 1 DONE** (1A generation: Test.mode/template_spec, build_template
  roll_kind, solid pre-bubbled roll discs proven scannable on the real Otsu path +0.55 margin,
  zero-padded roll; 1B scan identity: QR test_id guard→test_mismatch, verify-only roll reconcile→
  roll_mismatch, widened reason 20→32; 1C: wizard mode picker + writable mode + review labels).
  E2E: standard 15/15 on Chromium/Chrome/Edge + Mode-B 16/16 (auto-identify + tamper flag). Not yet
  merged. Next: Phase 2 (analytics core).

- 2026-06-19 — **Section-awareness sweep** (`738098b`→`0ac99e9`, main). Owner: "when starting a class
  test there is NO option to select for which section." Test wizard now has a type-aware Section Select
  → sets Test.class_group to the chosen tree node; class Exams list, class Overview counts, and the
  Generate roster picker all aggregate the class+section subtree (section badges/labels + filters).
  Students page → single filterable list; Subjects page polished. Screenshot-verified; lint/build clean.

- 2026-06-19 — **Exam workspace completed + E2E restored**. Built the exam Overview hub
  (/tests/:id) and a post-creation Questions editor (/tests/:id/questions: add/edit/delete/save
  with answer keys), extracted QuestionEditor to features/test/QuestionEditor.jsx (shared with the
  wizard), wired Build→questions + an Overview nav item. Restored e2e/run.mjs for the org-first IA
  (UI auth + OMR pipeline, API setup for org/class/students) — Chromium full loop green (14 steps).
