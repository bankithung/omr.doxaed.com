# Current State

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
- **Phase 7 (billing):** make the daily generation quota + scan caps PER-ORG (currently
  `GenerationEvent` counts per-user, so org members get separate quotas) + meter scans per org per
  period; gate org creation behind an active subscription.
- **Phase 8 hardening:** Celery+Redis async scanning (dev is eager); FILL_HIGH/LOW + fiducial
  calibration vs real photos; cropped review-region images; register-email enumeration; verify-email
  throttle; account lockout (django-axes); frontend code-splitting (bundle ~918 kB).
- **Leftovers:** question/option image upload API (models have ImageField, serializers omit);
  unused User.first_name/last_name; hand-authored form.jsx still unused; partial-marking net-zero
  counts as wrong (documented).

## Resolved
- P1 AllowAny · P2 child-scope 403 · P3 sheet header overlaps · P4 review-queue (needs_review/dedup/no_qr).
