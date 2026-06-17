# Current State

- 2026-06-17: **Phase 3 (Roster & OMR generation) complete** (branch `phase-3` → merged to `main`).
  Roster + Student (Fernet-encrypted `full_name`, named+roll OR count-only). The OMR engine:
  `geometry` (canonical-pixel template descriptor), `shuffle` (deterministic per-sheet
  question/option order + answer_key), `codes` (sheet_code), `generator` (ReportLab → multi-page
  PDF with QR/fiducials/roll-grid/answer-grid). Generation endpoint `POST /api/v1/omr/generate/`
  (one OmrSheet/student, batch PDF via PyMuPDF, free-tier gates ≤10 students/gen & ≤5 gens/day).
  **126 backend tests green.** QR round-trip test passes (rendered sheet's QR decodes back).
  **Visually validated** — a rendered sheet looks clean (fiducial quiet zones, readable grids).
  React: roster mgmt + generate-sheets flow (download batch PDF). The Phase-0 owner-scope DB
  constraint validated on real tables (Phase 2).
- **Next:** Phase 4 (Scanning & grading — the hardest phase) per `prompts/OMR_ENGINE_SPEC.md` +
  `BUILD_ROADMAP.md`: ScanBatch/ScanJob models, async (Celery — or eager-in-dev) OpenCV pipeline
  (QR decode → fiducial detect → perspective warp → roll-dot read → answer-bubble fill-ratio with
  hysteresis → multi-page stitch → grade against the per-sheet answer_key → StudentResult/
  QuestionResponse), a manual review queue for low-confidence reads, progress endpoint. Build a
  labeled fixture set EARLY (the generator can produce + simulate filled sheets for tests).
- Done: Phase 0 (foundations) · Phase 1 (auth) · Phase 2 (assessments) · Phase 3 (OMR generation).

## The generator↔scanner contract (CRITICAL for Phase 4)
Each `OmrSheet` stores `template_descriptor` (canonical 100-DPI, top-left-origin PIXEL coords:
fiducials, roll_grid origin/pitch/radius, qr region, answer_bubbles list of {q_pos, page,
options:[{label,cx,cy,r}]}, page_map) PLUS `question_order`/`option_order`/`answer_key`. The Phase-4
scanner MUST: decode the QR (`{sheet_code}|{page}|{total}`) → load the OmrSheet → detect the 4
fiducials → warp the scan to the canonical px space → read bubbles at the descriptor's exact cx/cy/r
→ grade detected printed-labels through `answer_key` + the test's MarkingScheme. The generator draws
at these exact descriptor coords (verified by the QR round-trip + visual check), so the scanner must
read at the same coords. NEVER grade against the test default order — always the sheet's answer_key.

## Architecture patterns (recap; FOLLOW)
- Direct `OwnerScopedModel` → `ScopedModelViewSet` (IsInScope). Child-scoped (Student→Roster,
  OmrSheet/ScanJob→Test) → `IsAuthenticated` + queryset filtered through the parent's scope.
- PII: `common.encryption.EncryptedTextField` (Fernet, key `FIELD_ENCRYPTION_KEY` from env).
- Free-tier gates enforced server-side; over cap → 403 with an upgrade message.

## Deferred follow-ups
- **Phase 4:** scanning uses Celery+Redis per spec; for local no-Docker dev, run Celery eager
  (`task_always_eager`) or install Memurai/Redis — defer the broker, process synchronously in dev.
  Build a fixture set (clean/faint/double/skewed). Print at known DPI; fiducial detection robustness
  tuned against fixtures.
- **Phase 6:** `IsInScope` org-membership path. **Phase 8:** register enumeration, verify-email
  throttle, account lockout, code-splitting. **Phase 3 leftover:** question/option image upload API
  (models have ImageField; serializers omit — text-only MVP).

## Resolved
- Phase-1 AllowAny applied. Phase-2 child-scope 403 bug fixed. Phase-3 sheet header/fiducial overlaps fixed.
