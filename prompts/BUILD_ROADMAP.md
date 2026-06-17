# Build Roadmap — OMRFlow

Build in phases. Each phase is shippable/testable on its own. Don't start a phase before the previous one's "done" criteria are met. MVP = Phases 1–5 (a single teacher can run the full loop). Phases 6–8 add orgs, billing, depth. Phase 9 is the mobile app.

## Phase 0 — Foundations
- Repo (separate `backend/` Django+DRF and `frontend/` React), Docker Compose (api, worker, postgres, redis, object storage, frontend dev server), settings via env vars.
- Django + DRF skeleton (JSON API), base apps created; React app scaffolded with Tailwind, routing, and an API client (JWT auth handling). CI (lint + tests) for both.
- Scaffold the **custom React UI component library** (Select, Modal, Confirm, Toast, Menu, Tabs, Table, form fields, Stepper, Progress, Empty state) on headless primitives + Tailwind. Nothing else uses native dropdowns/alerts after this.
- **Done when:** both apps run in Docker, the component library renders in a Storybook/style-guide page, CI green.

## Phase 1 — Accounts
- Signup, email verification, login/logout, password reset, profile.
- Argon2 hashing, throttling/lockout, secure cookies, JWT for API.
- **Done when:** a user can register, verify, log in, reset password; security checks in place; tests pass.

## Phase 2 — Assessments core (solo scope)
- ClassGroup → Test CRUD; Question + Option authoring; MarkingScheme.
- Retest creation (linked to parent test, attempt numbering).
- Solo owner-scope isolation enforced globally.
- **Done when:** a solo user can create a class, a test with MCQs and marking, and a retest; all scoped to them; tests pass.

## Phase 3 — Roster & OMR generation
- Roster + Student; two input modes (named+roll, or count-only).
- OMR PDF generation with ReportLab: header, per-page QR (`sheet_code` + page no/total), fiducials, roll-number dot grid, answer grid.
- **Multi-page sheets**: long tests overflow to extra pages with continued numbering; store `page_count` + `page_map`.
- Per-student shuffle + stored `question_order`/`answer_key`; batch PDF.
- Template descriptor (bubble geometry) stored for scanning.
- Free-tier limits enforced (10 students/gen, 5 gens/day).
- **Done when:** a user generates a correct, printable batch of personalized (and where needed multi-page) sheets; limits enforced; generation is deterministic and reproducible from stored data.

## Phase 4 — Scanning & grading
- Web upload + **live auto-detect capture** (camera auto-grabs sheets, no manual tap) and **bulk PDF/image** import with auto-split; ScanBatch/ScanJob (per page); Celery processing.
- Pipeline per `OMR_ENGINE_SPEC.md`: QR (sheet+page) → fiducials → warp → roll dots → answer grid → **assemble multi-page** → grade against per-sheet key → StudentResult/QuestionResponse.
- Review queue for flagged marks and missing pages; live progress reporting.
- Fixture-based engine tests (clean/faint/double/skewed/missing-QR/multi-page, pages out of order).
- **Done when:** sheets are graded fast and accurately, multi-page sheets stitch correctly in any scan order, doubtful marks/missing pages are flagged not guessed, and fixture tests meet target accuracy.

## Phase 5 — Analytics & export (MVP complete)
- Test-level (distribution, average, toppers, hardest questions, option distribution).
- Student-level; improvement view across a test→retest series.
- CSV/Excel export + printable PDF report. Charts via Recharts.
- **Done when:** a teacher can run the full loop end to end and read meaningful analytics, including improvement over retests.

## Phase 6 — Organizations & roles
- Org creation, invitations, membership, admin vs member roles.
- Org-scope isolation; admin sees all members' work within the org.
- Audit log.
- **Done when:** an admin can build a team, members work in the org workspace, admin has full oversight, and scope isolation holds across users.

## Phase 7 — Subscription & billing
- Plans (free/team/business[/enterprise]); Razorpay subscriptions + webhooks (signature-verified).
- Seat limits + scan caps enforced; upgrade/downgrade/cancel handling.
- **Done when:** an org can subscribe and pay, limits switch correctly by plan, webhooks reconcile state.

## Phase 8 — Hardening & polish
- Full security pass (OWASP Top 10 checklist), rate limiting review, PII encryption verified.
- Performance pass (indexes, query/aggregation tuning, scan throughput).
- Responsive QA at all breakpoints; empty/error/loading states; accessibility pass.
- **Done when:** security checklist complete, performance targets met, UI passes responsive + a11y QA.

## Phase 9 — Mobile app
- Build against the existing DRF API (e.g., Flutter or React Native).
- Core: auth, browse classes/tests, **capture & upload scans**, view results/analytics. Heavy processing stays server-side.
- **Done when:** the app reuses the API to run scanning and view results on mobile.

---

### Sequencing notes
- Keep API-first throughout so Phase 9 needs no backend rework.
- The custom component library (Phase 0) is a prerequisite for *every* UI screen — don't skip it.
- The OMR engine (Phases 3–4) is the riskiest part; budget extra time and lean on the fixture set early.
