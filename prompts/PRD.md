# PRD — OMRFlow

## 1. Vision

Let teachers and institutions create MCQ tests, generate personalized printable OMR sheets, scan completed sheets in seconds with a phone or scanner, auto-grade them, and track each student's improvement across retests — all in one secure, fast, mobile-responsive platform.

## 2. Problem

Manual MCQ grading is slow and error-prone. Existing OMR tools are clunky, desktop-bound, need special scanners, can't shuffle questions per student reliably, and give shallow analytics. Small schools and individual tutors get priced out.

## 3. Target users

- **Individual tutors / teachers** — solo, free tier, occasional tests.
- **Coaching centers / schools** — an organization with many staff, recurring tests, need oversight and analytics.
- **Org admins** — manage members, billing, and see everything members do.

> A **student** (test-taker) is *not* a platform user. They fill a paper sheet. Their identity lives as a record inside a test, not as an account. This is central to the data model and billing.

## 4. Roles & permissions

| Capability | Free (solo) | Org Member (Teacher) | Org Admin |
|---|---|---|---|
| Create classes, tests, questions | ✓ | ✓ | ✓ |
| Generate OMR sheets | ✓ (limited) | ✓ | ✓ |
| Scan & grade | ✓ (limited) | ✓ | ✓ |
| View own analytics | ✓ | ✓ | ✓ |
| View **all members'** work & analytics | — | — | ✓ |
| Invite/remove members | — | — | ✓ |
| Manage subscription & billing | — | — | ✓ |
| Audit log | — | — | ✓ |

## 5. Core features (by epic)

### E1 — Accounts & Organizations
- Email/password signup, email verification, password reset. **Anyone can sign up for free.**
- A free user works solo on the free tier. To get an organization, the user **creates one, which requires a paid subscription** — there is no free org tier.
- **"Admin" is not a separate account type.** The user who creates (and pays for) an org is automatically its admin.
- The admin invites other signed-up users as members by email; members join the org workspace. The admin oversees everything members do.
- All data is scoped to either a solo user or an org (strict isolation).

### E2 — Class & Test hierarchy
- **Class** (e.g., "Class 8") → contains **Tests** (e.g., "Test 1").
- A **Test** has: title, subject, MCQ questions, options, correct answers, marking scheme.
- **Retest**: create another attempt of the *same* test, linked to the original, so improvement can be compared. A test can have many retests forming an attempt series.
- Marking scheme per test: marks per correct answer, optional negative marking, optional partial marking, single vs multiple correct.

### E3 — Question authoring
- Add MCQ questions: question text, 2–6 options, mark correct option(s).
- Optional: question images, section/topic tags, difficulty.
- Optional reusable **question bank** so questions can be pulled into multiple tests. *(Phase 2)*

### E4 — Student roster
- Two ways to define test-takers:
  1. **Pre-enter names + assign roll numbers** in advance.
  2. **Just pick a count** (e.g., 20 anonymous sheets numbered 1–20) and attach names after scanning.
- A roster can be saved per class and reused across tests.

### E5 — OMR sheet generation
- Generate printable OMR sheets (PDF) for a test.
- **Per-student personalization**: optionally shuffle question order (and/or option order) uniquely per student to deter copying. Each sheet stores its own answer-key version.
- Each sheet carries: institution/test header, pre-printed student name (if known), a **bubbled roll-number grid**, a **QR code** (encodes test ID + student/sheet ID + shuffle-version), corner **fiducial markers** for alignment, and the question bubble grid.
- Batch generate (e.g., 20 sheets) into one print-ready PDF.
- See `OMR_ENGINE_SPEC.md` for full layout + reliability rules.

### E6 — Scanning & grading
- **Auto-detect, no manual capture.** Point the camera (or feed a stack) and sheets are detected and grabbed automatically — no per-sheet capture tap. Also accepts a multi-page PDF / image folder from a scanner, auto-split.
- **Multi-page sheets auto-stitch.** Long tests print across pages; each page self-identifies via QR (page i of n), so pages scanned in any order are grouped into one result. Missing pages are flagged.
- Pipeline: read QR → align via fiducials → detect filled dots → assemble pages → map to that sheet's answer-key version → grade.
- **Fast**: server-side OpenCV, async batch processing with live progress.
- **Reliable**: ambiguous marks (double-marked, faint, smudged) and missing pages go to a **manual review queue** instead of being guessed.
- Output: per-student score, per-question correctness, and a class result set.

### E7 — Analytics
- **Test-level**: score distribution, average/median, topper list, hardest questions (most-missed), per-option choice distribution.
- **Student-level**: score, accuracy by topic/section.
- **Improvement view**: compare a student (or whole class) across the test → retest series; show deltas and trends.
- **Org-level** (admin): activity across members, tests run, scans processed.
- Export results to CSV/Excel and a printable PDF report.

### E8 — Subscription & billing
- See Monetization below. Razorpay for payments (₹ / India). Plan gates enforced server-side.

## 6. Monetization

> **Confirmed model:** Anyone signs up free and works solo on the free tier. **Creating an organization requires a paid subscription — there is no free org.** The org creator is its admin. A "seat" = a staff member who can log in (admin counts as one seat); test-takers are never accounts. Seat caps/prices below are proposed — confirm the numbers.

| Plan | Who | Price | Seats | Scans/month | Other limits |
|---|---|---|---|---|---|
| **Free** | Solo, no org | ₹0 | 1 | 200 | 10 students/generation, 5 generations/day. All core features. |
| **Team** | Org | **₹500/mo** | up to **50** | **5,000** (shared by org) | Unlimited generations. Admin oversight, audit log. |
| **Business** | Org | **₹1,000/mo** | **51–200** | **20,000** (shared by org) | Everything in Team + priority scan queue. |
| **Enterprise** | Org, custom | Custom | 200+ | Custom | SSO, support SLA, custom caps. |

Rules:
- **Past a cap:** block the next scan/generation with an upgrade prompt — **no silent overage**. (A paid top-up pack can be added later.)
- **Annual billing:** pay for 10 months, get 12 (2 months free) — recommended for retention.
- **Scans are the metered dimension** (they're the main server cost); generations are unlimited on paid plans.
- Free→paid upgrade is instant; downgrade/cancel takes effect at period end.

> These numbers are sensible defaults, **not** validated against real costs or demand — revisit after launch. Note that ₹500 for up to 50 seats is very generous (~₹10/seat); consider whether that's sustainable before going live. Pricing is a business decision; treat this as a recommendation, not financial advice.

## 7. Non-functional requirements

- **Responsive**: every screen works cleanly from 320px phones to large desktops. Mobile-first layout.
- **Custom UI only**: no native `<select>` dropdowns, no browser `alert()`/`confirm()`. All selects, menus, dialogs are custom-styled components. Confirmations and messages use custom modals/toasts. (See `DESIGN_SYSTEM.md`.)
- **Concise copy**: short, precise text everywhere. No walls of text.
- **Performance**: page loads fast; single-sheet scan target < ~1s server-side; batch scans processed async with progress.
- **Security**: encrypted in transit (TLS) and sensitive PII encrypted at rest; strict org-level data isolation; rate limiting; OWASP Top 10 mitigations; secure payment handling (no card data stored). (See `TECHNICAL_ARCHITECTURE.md → Security`.)
- **Reliability**: scan results are auditable; nothing is silently mis-graded — low-confidence reads are flagged.
- **Accessibility**: keyboard-navigable, sufficient contrast, focus states.

## 8. Primary user flows

1. **Solo quick test**: Sign up → create Class 8 → create Test 1 → add 10 MCQs → set marking → enter/skip roster → generate 10 OMR PDFs → print → students fill → scan batch → view results.
2. **Org recurring test**: Admin creates org → invites teachers → teacher creates test + roster (named, roll numbers) → generates shuffled personalized sheets → scans → reviews flagged marks → publishes results → creates a retest later → compares improvement.
3. **Admin oversight**: Admin opens org dashboard → sees all tests/scans by members → org-level analytics → manages seats and billing.

## 9. Out of scope (v1)

- Subjective/long-answer grading (MCQ only).
- Native mobile app (v1 is responsive web; app comes after, reusing the API).
- Live online test-taking (this is paper-OMR, not on-screen quizzes).
- Multi-language UI (English first).
- Public question marketplace.

## 10. Success metrics

- Time from scan upload to graded result.
- % of sheets auto-graded without manual review (reliability).
- Tests created / sheets scanned per active org.
- Free→paid conversion; paid retention.
