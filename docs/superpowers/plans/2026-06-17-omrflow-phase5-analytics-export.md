# OMRFlow Phase 5 (Analytics & export) Implementation Plan — COMPLETES THE MVP

> Standalone repo `projects/omr.doxaed.com/` (own `.git`), branch `phase-5`. Paths relative to repo
> root (`backend/...`). Commit to THIS repo. TDD; `- [ ]` steps. venv `backend/.venv`.

**Goal:** A teacher reads meaningful analytics for a test (distribution, average/median, toppers,
hardest/most-missed questions, per-option choice distribution), per-student accuracy, and improvement
across a test→retest series; and exports results as CSV/Excel and a printable PDF report. Charts via
Recharts. This finishes the MVP (Phases 1–5).

**Architecture:** Read-only aggregation endpoints in the `analytics` app over `StudentResult` +
`QuestionResponse` (scoped via `test__user`). No new tables. Per-student SHUFFLE is handled by
mapping printed positions/labels back to the underlying Question/Option via each `OmrSheet`'s stored
`question_order`/`option_order`. Export endpoints stream CSV (stdlib), Excel (openpyxl), and a PDF
report (ReportLab).

## Locked decisions
- **D1 Shuffle-correct aggregation:** `QuestionResponse.question` (FK) must identify the UNDERLYING
  question. FIRST ensure grading populates it (`question = Question(id=omr_sheet.question_order[q_pos])`);
  analytics groups hardest/most-missed by `question`. Per-option distribution maps each printed marked
  label → original option label via `omr_sheet.option_order` before counting.
- **D2 Endpoints (scoped, IsAuthenticated, child-scope via `test__user`):**
  - `GET /api/v1/analytics/test/{test_id}/` → test-level summary (below).
  - `GET /api/v1/analytics/test/{test_id}/improvement/` → retest-chain improvement (per student across attempts).
  - `GET /api/v1/analytics/test/{test_id}/export/?format=csv|xlsx|pdf` → file download.
- **D3 Score % uses `score/max_score`** (guard max_score==0). Distribution buckets: 0–20/21–40/41–60/
  61–80/81–100 % of max.
- **D4 Improvement:** walk `Test.parent_test` to the root, collect the chain (ordered by
  `attempt_number`); for each student (matched by `student_id`, or roll_number across rosters) list
  their score per attempt + delta vs the previous attempt.

## Test-level summary shape
```
{ test: {id,title,subject,attempt_number}, n_students, graded, needs_review_count,
  average, median, max, min, max_score,
  distribution: [{bucket:"0-20%", count}, ...],
  toppers: [{student:{roll,name}, score, max_score}, ... up to 5],
  hardest_questions: [{question_id, order_index, text, wrong_rate, n}, ... sorted desc],
  option_distribution: [{question_id, text, options:[{label, count}], correct:[labels]}, ...] }
```

## File structure
- `backend/analytics/{services.py (pure aggregation fns), views.py, serializers.py, urls.py, export.py}`.
- `backend/analytics/tests_analytics.py`.
- (Small tweak) `backend/omr/scan/pipeline.py` — set `QuestionResponse.question` during grading.
- Frontend: `src/api/analytics.js`, `routes/Analytics.jsx` (+ improvement view), export buttons.

---

## Task 1: Ensure question FK + Test-level analytics (TDD)
- [ ] **Grading tweak:** in `omr/scan/pipeline.py` where `QuestionResponse`s are created, set
  `question_id = omr_sheet.question_order[q_pos]` (the underlying Question). Add/confirm a test that a
  graded QuestionResponse has the correct underlying `question`. (If already set, skip.) Re-run the
  Phase-4 round-trip tests → still green.
- [ ] **`analytics/services.py`** pure functions over a test's StudentResults:
  - `test_summary(test) -> dict`: n_students, graded, needs_review_count, average/median/max/min of
    `score`, `max_score`, `distribution` (5 buckets by score%), `toppers` (top 5), `hardest_questions`
    (group QuestionResponses by `question`, wrong_rate = wrong/n, join question text + order_index,
    sort desc), `option_distribution` (per question: map each response's printed marked label →
    original via the response's `student_result.omr_sheet.option_order`, count per original label;
    include the correct original labels).
- [ ] **`GET /api/v1/analytics/test/{test_id}/`** view (IsAuthenticated; `get_object_or_404(Test,
  id=..., user=request.user)`); serialize the summary. Register routes; include in config/urls.
- [ ] **Tests:** build a test + a few students + StudentResults/QuestionResponses (or run the Phase-4
  pipeline on simulated scans) with known scores → assert average/median/distribution/toppers; a
  question everyone got wrong is top of hardest_questions; option_distribution counts map correctly
  even with option shuffle (construct a sheet with a known option_order). Cross-tenant test → 404.
- [ ] Commit `feat(analytics): test-level analytics endpoint (shuffle-correct)`.

## Task 2: Student-level + improvement (retest) analytics (TDD)
- [ ] `analytics/services.py`: `student_detail(student_result) -> dict` (score, max, %, correct/wrong/
  blank, per-question {order_index, text, is_correct, flagged, marked→original}); `topic_accuracy`
  (group the student's responses by the question's `topic`, accuracy per topic).
- [ ] `improvement(test) -> dict`: resolve the retest chain (walk `parent_test` to root, order by
  `attempt_number`); for each student present in any attempt, list `[{attempt_number, score, max_score,
  pct, delta_vs_prev}]`; also a class-level average per attempt + trend.
- [ ] Views: `GET /api/v1/analytics/test/{test}/student/{student_id}/` and
  `GET /api/v1/analytics/test/{test}/improvement/`. Scoped.
- [ ] Tests: a test→retest with a student improving across attempts → deltas correct, class average per
  attempt; student_detail topic accuracy. Commit `feat(analytics): student detail + retest improvement`.

## Task 3: Export — CSV / Excel / PDF report (TDD)
- [ ] Install `openpyxl`; `pip freeze > requirements.txt`.
- [ ] `analytics/export.py`: `results_csv(test) -> bytes` (rows: roll, name, score, max, correct, wrong,
  blank, needs_review); `results_xlsx(test) -> bytes` (openpyxl workbook, a results sheet + a summary
  sheet); `report_pdf(test) -> bytes` (ReportLab: header, the test_summary stats, a simple
  score-distribution table/bars, toppers, hardest questions).
- [ ] `GET /api/v1/analytics/test/{test}/export/?format=csv|xlsx|pdf` → returns the file with the right
  `Content-Type` + `Content-Disposition` attachment filename. Scoped.
- [ ] Tests: each format returns 200 with non-empty body + correct content-type; the CSV has one row
  per student; cross-tenant → 404. Commit `feat(analytics): CSV/Excel/PDF export`.

## Task 4: Frontend — analytics dashboards + export (TDD-light, build-verified)
- [ ] `src/api/analytics.js`: `getTestAnalytics(testId)`, `getImprovement(testId)`,
  `getStudentDetail(testId, studentId)`, `exportUrl(testId, format)` (via `mediaUrl`/api origin).
- [ ] `routes/Analytics.jsx` (protected, `/tests/:testId/analytics`): summary cards (n, average,
  median, needs-review); a Recharts BarChart of the score distribution (reuse `@/components/ui/chart`
  or Recharts directly); toppers list; hardest-questions table; option-distribution (small bars per
  question); Export buttons (CSV/Excel/PDF → open `exportUrl`). An "Improvement" tab/section showing a
  Recharts line of class average per attempt + a per-student delta table (when a retest chain exists).
- [ ] Add an "Analytics" action/link on each test row in `TestList.jsx`. Custom components only; build clean.
- [ ] Commit `feat(analytics): analytics dashboards + export UI`.

## Task 5: Phase 5 wrap-up + review + merge — MVP COMPLETE
- [ ] Full backend suite + check + frontend build green; `makemigrations --check` clean.
- [ ] Review (aggregation correctness incl. shuffle mapping, export integrity, scope). Visual
  spot-check: render a PDF report, eyeball it.
- [ ] Memory: mark MVP (Phases 1–5) COMPLETE; note Phases 6–9 remaining (orgs, billing, hardening,
  mobile). Merge `phase-5` → `main`.

## Self-review
- Coverage: test-level ✓(T1), student+improvement ✓(T2), export ✓(T3), dashboards+export UI ✓(T4),
  wrap-up ✓(T5). Shuffle handled via question_order/option_order mapping (D1). All endpoints scoped.
- Deferred: org-level analytics (Phase 6); advanced charts/insights; caching heavy aggregations (Phase 8).
