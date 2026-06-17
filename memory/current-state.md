# Current State

- 2026-06-17: **Phase 4 (Scanning & grading) complete** (branch `phase-4` → merged to `main`).
  The full OMR engine round-trips: **generate → fill → scan → grade**. OpenCV pipeline
  (`omr/scan/`): `align` (QR decode → fiducial detect → perspective warp to canonical),
  `read` (roll + answer bubbles via fill-ratio + hysteresis), `grade` (per-sheet answer_key +
  MarkingScheme), `pipeline` (orchestrate, multi-page stitch, review flags, StudentResult/
  QuestionResponse/ReviewItem). A **synthetic simulator** (`omr/simulate.py`) fills generated
  sheets at descriptor coords → enables a full automated round-trip (perfect-score test passes).
  Endpoints: `POST /omr/scan/` (eager/sync processing in dev), batch progress, results, review
  queue + resolve. **233 backend tests green**; reviewed GRADING-SOUND & SCOPE-SECURE (live
  cross-tenant probe). React: scan upload+progress, results table+drilldown, review queue.
- **Next:** Phase 5 (Analytics & export — COMPLETES THE MVP) per `prompts/PRD.md` (E7) +
  `BUILD_ROADMAP.md`: test-level analytics (score distribution, average/median, toppers,
  hardest/most-missed questions, per-option choice distribution), student-level (accuracy by
  topic), improvement view across a test→retest series (deltas/trends), CSV/Excel export +
  printable PDF report, charts via Recharts. Aggregation endpoints (scoped) + React dashboards.
- Done: Phase 0 · 1 (auth, 26) · 2 (assessments, 45) · 3 (OMR gen, 126) · 4 (scan/grade, 233 total).

## The OMR engine (recap for analytics + future)
StudentResult (score/max/correct/wrong/blank/needs_review) + QuestionResponse (q_pos, marked,
is_correct, flagged) per student per test. Retest chain via `Test.parent_test`/`attempt_number`;
improvement analytics compare a student's StudentResults across the chain. Grading always uses the
OmrSheet's stored `answer_key` (per-sheet shuffle). Low-confidence reads → ReviewItem (never guessed).

## Architecture patterns (recap)
- Direct `OwnerScopedModel` → `ScopedModelViewSet` (IsInScope). Child-scoped (everything under a
  Test: Question, OmrSheet, ScanJob, StudentResult, ReviewItem, …) → `IsAuthenticated` + queryset
  filtered through `test__user` (or `omr_sheet__test__user`, `scan_job__batch__test__user`).
- PII: `common.encryption.EncryptedTextField`. Free-tier gates server-side (403 + upgrade msg).
- Scanning is EAGER/sync in dev (no Celery broker); Celery+Redis = a prod/Phase-8 enhancement.

## Deferred follow-ups
- **Phase 8 hardening:** Celery+Redis async scanning; threshold (FILL_HIGH/LOW) calibration vs real
  photos; fiducial detection robustness vs logos; cropped review-region images; register enumeration;
  verify-email throttle; account lockout; frontend code-splitting (bundle ~890 kB).
- **Phase 6:** `IsInScope` org-membership path. **Phase 3 leftover:** question/option image upload API.
- **Partial-marking note:** a question with net-zero partial credit counts as wrong_count (documented).

## Resolved
- Phase-1 AllowAny. Phase-2 child-scope 403. Phase-3 sheet header overlaps. Phase-4 review-queue
  (needs_review clear, double_mark dedup, no_qr surfaced).
