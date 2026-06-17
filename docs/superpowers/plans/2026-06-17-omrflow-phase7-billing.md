# OMRFlow Phase 7 (Subscription & billing) Implementation Plan

> Standalone repo `projects/omr.doxaed.com/` (own `.git`), branch `phase-7`. Paths relative to repo
> root (`backend/...`). Commit to THIS repo. TDD; `- [ ]` steps. venv `backend/.venv`.

**Goal:** Organizations subscribe to plans (Free / Team ₹500 / Business ₹1000 / Enterprise) via
Razorpay; plan limits (seats, monthly scans, daily generations, students-per-generation) are enforced
SERVER-SIDE per org; webhooks (signature-verified) keep subscription state in sync. Free org = 1 seat
(admin only); adding staff / higher caps requires a paid subscription.

**Architecture:** `billing` app: `Plan` (seeded tiers) + `Subscription` (per org). A `plan_limits`
service resolves the org's active plan (paid Subscription or the Free defaults) and enforces gates.
Razorpay calls hide behind `billing/gateway.py` (mocked in tests); the webhook verifies the HMAC
signature. **Razorpay keys come from env (`RAZORPAY_KEY_ID`/`_KEY_SECRET`/`_WEBHOOK_SECRET`); a real
charge needs the user's keys — everything else is testable with mocks + a test secret.**

## Locked decisions
- **D1 Plans (seeded):** `free` (price 0, seat_limit 1, students_per_generation_limit 10,
  generations_per_day_limit 5, monthly_scan_limit 50), `team` (₹500, seats 50, gens/students unlimited
  [null], monthly_scan 5000), `business` (₹1000, seats 200, monthly_scan 20000), `enterprise`
  (custom/null limits). Numbers are validate-before-launch starting points (per PRD). Seed via a data
  migration or `python manage.py seed_plans` idempotent command.
- **D2 Org plan resolution:** `org_plan(org)` = the `Plan` of the org's `active` Subscription, else the
  `free` Plan. `null` limit = unlimited.
- **D3 Gates (per ORG, server-side):** seat (active membership count < seat_limit before invite/accept);
  generations/day (per org), students/generation, monthly scans (per org, calendar month) — over cap →
  403 with an upgrade message. Fixes the Phase-6 per-user-quota gap (count per org now).
- **D4 No hard org-creation paywall** (keeps dev/tests working): org creation stays open; a new org is on
  the free plan (1 seat). Inviting a 2nd member requires a paid sub (seat gate). Documented as the
  pragmatic interpretation of the spec's "paid org" (monetize via the seat gate).
- **D5 Razorpay via `billing/gateway.py`:** `create_subscription(plan, org)`, `verify_webhook(body, sig)`
  (HMAC-SHA256 of the raw body with `RAZORPAY_WEBHOOK_SECRET`). Tests MOCK `create_subscription` and use a
  real signature for `verify_webhook`. Keys default to test placeholders in `.env(.example)`.

## Models (`billing/models.py`)
- `Plan`: code (unique), name, price_inr (Decimal), seat_limit (int null=unlimited),
  students_per_generation_limit (int null), generations_per_day_limit (int null), monthly_scan_limit
  (int null), razorpay_plan_id (char blank).
- `Subscription`: organization (OneToOne), plan FK, status (active|past_due|canceled|created),
  razorpay_subscription_id (char blank), current_period_end (datetime null), seats_purchased (int),
  created_at/updated_at.

---

## Task 1: Plan + Subscription models + plan_limits service + per-org quotas (TDD)
- [ ] `billing/models.py` (Plan, Subscription). makemigrations + migrate. A `seed_plans` management command (idempotent `update_or_create` for the 4 tiers).
- [ ] `billing/limits.py`: `org_plan(org) -> Plan` (active sub's plan or free); `seat_count(org)`,
  `can_add_seat(org)`, `generations_today(org)`, `can_generate(org, n_students)`,
  `scans_this_month(org)`, `can_scan(org)`. Use the org's Subscription/plan; `null` = unlimited.
- [ ] Make generation/scan counting PER-ORG: add `organization` FK (null for solo) to `omr.GenerationEvent`;
  add a `ScanEvent` (organization null, user, created_at) recorded on each scan job processed (or per
  batch). For solo, keep per-user. Migrate.
- [ ] Tests: free plan → can_add_seat False at 1 member, can_generate False for 11 students / 6th gen,
  can_scan False past 50; a `team` Subscription → higher limits; solo unaffected (uses the free
  constants / per-user as today).
- [ ] Commit `feat(billing): Plan/Subscription models + per-org plan limits service`.

## Task 2: Razorpay gateway + subscribe endpoint + webhook (TDD, mocked)
- [ ] Install `razorpay`; `pip freeze > requirements.txt`. Add `RAZORPAY_KEY_ID`/`RAZORPAY_KEY_SECRET`/
  `RAZORPAY_WEBHOOK_SECRET` to settings (from env; placeholders in `.env`/`.env.example`).
- [ ] `billing/gateway.py`: `get_client()` (razorpay.Client with the env keys), `create_subscription(org,
  plan) -> dict` (calls the SDK; returns subscription id + short_url — wrapped so it can be MOCKED),
  `verify_webhook_signature(raw_body: bytes, signature: str) -> bool` (`hmac.new(secret, raw_body,
  sha256).hexdigest()` compared with `hmac.compare_digest`).
- [ ] `POST /api/v1/billing/organizations/{id}/subscribe/` `{plan_code}` (org ADMIN only) → calls
  `create_subscription`, creates/updates the org's Subscription (status `created`), returns the
  subscription id + checkout info for the frontend. (Live needs real keys; tests MOCK create_subscription.)
- [ ] `POST /api/v1/billing/webhook/` (AllowAny, raw body): verify the `X-Razorpay-Signature` header via
  `verify_webhook_signature` (400 if invalid); parse the event; on `subscription.activated`/`charged` →
  set the org's Subscription `active` + `current_period_end`; on `subscription.cancelled`/`halted` →
  `canceled`/`past_due`. Idempotent.
- [ ] Tests: subscribe (mocked gateway) creates a Subscription(created); a webhook with a VALID signature
  (computed with the test secret) activates it; an INVALID signature → 400; non-admin subscribe → 403.
- [ ] Commit `feat(billing): Razorpay gateway + subscribe endpoint + signature-verified webhook`.

## Task 3: Enforce gates + plan/usage endpoint (TDD)
- [ ] Apply gates: the org invite endpoint checks `can_add_seat` (else 403 upgrade); the generation
  endpoint uses `can_generate` per org (replace the per-user GenerationEvent check in org context); the
  scan endpoint checks `can_scan` + records a ScanEvent. Solo behavior unchanged.
- [ ] `GET /api/v1/billing/organizations/{id}/plan/` (member) → `{plan, status, current_period_end,
  usage:{seats, generations_today, scans_this_month}, limits}`.
- [ ] Tests: over-seat invite → 403; over-cap generate/scan → 403 with an upgrade message; an org on a
  `team` sub can invite > 1 + scan more; the plan/usage endpoint returns correct numbers. Solo unaffected.
- [ ] Commit `feat(billing): enforce per-org plan gates + plan/usage endpoint`.

## Task 4: Frontend — billing UI
- [ ] `src/api/billing.js` (getPlan, subscribe). `routes/Billing.jsx` (protected, `/organizations/:id/billing`,
  admin): show current plan + usage bars (seats/scans/generations vs limits), the tier cards (Free/Team/
  Business) with a Subscribe button → `subscribe(plan_code)` → (if Razorpay key present) open the Razorpay
  Checkout with the returned subscription id; else show "configure Razorpay keys" notice. Show upgrade
  prompts. Surface 403 upgrade errors from gated actions (generate/scan/invite) with a link to billing.
- [ ] Build clean. Commit `feat(billing): billing & subscription UI`.

## Task 5: Phase 7 wrap-up + review + merge
- [ ] Full backend suite + check + frontend build; `makemigrations --check`. Review (gate enforcement,
  webhook signature security, no secrets committed, scope). Memory + note the LIVE-KEYS requirement +
  recommend a dedicated payments security review before production. Merge `phase-7` → `main`.

## Self-review
- Billing models + per-org limits + gates + webhook signature verification are all TDD'd with a mocked
  gateway. The only live dependency is the user's Razorpay keys (env) for a real charge — flagged.
- Deferred: proration on plan change; dunning/retries; invoices; annual billing (2 months free) UI.
