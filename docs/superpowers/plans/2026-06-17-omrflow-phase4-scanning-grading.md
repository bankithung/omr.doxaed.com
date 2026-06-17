# OMRFlow Phase 4 (Scanning & grading) Implementation Plan

> Standalone repo `projects/omr.doxaed.com/` (own `.git`), branch `phase-4`. Paths relative to repo
> root (`backend/...`). Commit to THIS repo. TDD; `- [ ]` steps. venv `backend/.venv`.

**Goal:** Upload scanned OMR sheets (image or multi-page PDF) → the server reads them with OpenCV
(QR → fiducials → perspective warp → roll-number dots → answer bubbles via fill-ratio), stitches
multi-page sheets, grades against each sheet's stored `answer_key` + the test's `MarkingScheme`, and
produces `StudentResult`/`QuestionResponse`, routing low-confidence reads to a manual review queue.

**Architecture:** A pure-Python CV pipeline in `omr/scan/` operating on numpy images + the stored
`template_descriptor`. The crux test strategy is a **synthetic round-trip**: `omr/simulate.py`
renders a generated sheet and "fills" chosen bubbles at the descriptor's exact coords, producing a
fake scan; the pipeline must recover exactly those answers. Scanning runs **synchronously (eager)**
in dev (no Celery broker); the endpoint creates `ScanBatch`/`ScanJob` and processes inline.

**Tech:** OpenCV 4.13 + numpy, pyzbar (QR), PyMuPDF (PDF→image + the simulator's render), Pillow.

## Locked decisions
- **D1 Async:** process inline/eager in dev (no Redis). A `process_scan_job(job)` function does the
  work; the endpoint calls it synchronously. (Celery+Redis = a prod/Phase-8 enhancement — documented.)
- **D2 Canonical space:** warp every scan to the descriptor's 827×1169 px canonical space using the 4
  fiducial centers (homography), so bubbles are read at the descriptor's exact cx/cy/r.
- **D3 Fill classification:** for each bubble sample the INNER disc (radius `r*0.6`, to ignore the
  printed outline ring) in the warped, Otsu-thresholded image; `fill_ratio = dark/total`. Hysteresis:
  `>= FILL_HIGH (0.45)` → filled, `<= FILL_LOW (0.20)` → empty, between → ambiguous(flag). Constants
  calibrated against synthetic fixtures; expose them for tuning.
- **D4 Review flags → ReviewItem:** `no_qr`, `alignment` (fiducials not found), `roll_unreadable`
  (no clear digit / mismatch vs QR student), `double_mark` (2+ filled when single-correct expected),
  `faint` (ambiguous), `missing_page`. Never guess — flag.
- **D5 Stitch:** group `ScanJob`s by `omr_sheet`; grade only when all `page_count` pages are `done`;
  missing → `ReviewItem(missing_page)`, sheet stays `partial`.
- **D6 Grade:** detected printed labels → `answer_key[str(printed_pos)]`; correct iff the marked
  printed-label set equals the correct set (respect `multiple_correct_allowed`; `partial_marking`
  gives proportional credit); apply MarkingScheme (marks_per_correct, negative_marks_per_wrong).
  ALWAYS grade via the sheet's stored answer_key, never the test default.
- **D7 Models:** ScanBatch/ScanJob in `omr`; StudentResult/QuestionResponse/ReviewItem in `results`.
  All child-scoped (via test) → `IsAuthenticated` + queryset filtered through `test__user`.

## File structure
- `backend/omr/models.py` (+ ScanBatch, ScanJob), `backend/results/models.py` (StudentResult,
  QuestionResponse, ReviewItem).
- `backend/omr/simulate.py` — `simulate_scan(descriptor, sheet_meta, marked, roll, transform=None) -> ndarray`.
- `backend/omr/scan/align.py` (`decode_qr`, `detect_fiducials`, `warp_to_canonical`),
  `scan/read.py` (`read_roll`, `read_answers`), `scan/grade.py` (`grade_sheet`),
  `scan/pipeline.py` (`process_image(image)` orchestrator + `process_scan_job`).
- `backend/omr/serializers.py`/`views.py`/`urls.py` (+ scan upload, progress, review endpoints).
- Tests: `omr/tests_scan.py` (the synthetic round-trips), `results/tests_results.py`.
- Frontend: `src/api/scan.js`, `routes/Scan.jsx`, `routes/Results.jsx`, `routes/ReviewQueue.jsx`.

---

## Task 1: Scan + result models (TDD)
- [ ] `backend/omr/models.py` add `ScanBatch` (test FK, created_by, status [queued/processing/done],
  total, processed, created_at) and `ScanJob` (batch FK, omr_sheet FK null, page_no int, image_file
  FileField, status [queued/done/needs_review/failed], confidence float null, error_reason text).
- [ ] `backend/results/models.py`: `StudentResult` (test, student null, omr_sheet, score, max_score,
  correct_count, wrong_count, blank_count, needs_review bool, graded_at), `QuestionResponse`
  (student_result FK, question FK null, q_pos int, marked_options JSON, is_correct bool, flagged bool),
  `ReviewItem` (scan_job FK null, omr_sheet FK null, question FK null, reason char, resolved bool,
  resolved_by FK null, resolution JSON null, created_at). makemigrations + migrate. Add a basic model
  test (create the chain). Commit `feat(scan): ScanBatch/ScanJob + StudentResult/QuestionResponse/ReviewItem`.

## Task 2: Synthetic scan simulator (TDD — the test enabler)
- [ ] `backend/omr/simulate.py`: `render_canonical_image(descriptor, sheet_meta) -> ndarray` renders the
  sheet (reuse `generator.render_sheet_pdf` → PDF → `fitz` pixmap at 100 DPI → grayscale ndarray sized
  to `page_px`). `simulate_scan(descriptor, sheet_meta, marked, roll, page=0, transform=None) -> ndarray`:
  start from the rendered canonical image, then DRAW FILLED black discs (cv2.circle filled, radius
  `r*0.7`) at the descriptor coords for: each marked option `marked[q_pos] = [labels]` on that page, and
  each roll digit's bubble (roll_grid). If `transform` given (a 3x3 homography or rotation+scale), warp
  the image so the pipeline must un-warp it (tests robustness). Return uint8 grayscale.
- [ ] Test: simulate a sheet → the QR still decodes (`pyzbar`), and the image is the expected size. Commit
  `feat(scan): synthetic scan simulator (render + fill bubbles)`.

## Task 3: Alignment — QR + fiducials + warp (TDD)
- [ ] `backend/omr/scan/align.py`:
  - `decode_qr(image) -> (sheet_code, page, total) | None`: `pyzbar.decode`; parse `a|b|c`.
  - `detect_fiducials(image, descriptor) -> np.ndarray(4,2) | None`: threshold (Otsu inverse), find
    contours, keep large near-square solid blobs, take the one nearest each of the 4 expected corners
    (scale the descriptor fiducial positions to the image size as a prior); return ordered TL,TR,BL,BR
    centers in image coords, or None if any corner missing.
  - `warp_to_canonical(image, src_pts, descriptor) -> ndarray`: `cv2.getPerspectiveTransform(src_pts,
    dst_pts)` where dst = descriptor fiducial centers (canonical px); `cv2.warpPerspective` to
    `(page_px[0], page_px[1])`. Return grayscale canonical image.
- [ ] Tests: simulate a sheet WITH a perspective `transform`, then `detect_fiducials` finds 4 points and
  `warp_to_canonical` produces an image where a known fiducial center lands within a few px of the
  descriptor position (assert the warped fiducial alignment). Commit `feat(scan): QR + fiducial detection + perspective warp`.

## Task 4: Reading — roll + answers via fill-ratio (TDD — KEY round-trip)
- [ ] `backend/omr/scan/read.py`:
  - `bubble_fill_ratio(canonical_bin, cx, cy, r) -> float`: mask the inner disc (`r*0.6`), ratio of dark
    px. (Pass an Otsu/adaptive-thresholded binary image.)
  - `read_roll(canonical_bin, descriptor) -> (roll_str, flags)`: per digit-column, the row (0–9) with the
    highest fill above FILL_HIGH is that digit; ambiguous/none → flag `roll_unreadable`.
  - `read_answers(canonical_bin, descriptor, page, multiple_allowed) -> {q_pos: {marked:[labels],
    flag:str|None}}`: per question on `page`, classify each option via hysteresis; one filled → that
    label; none → blank; 2+ when not multiple_allowed → flag `double_mark`; ambiguous → flag `faint`.
- [ ] **KEY round-trip tests:** for a descriptor + chosen `marked`/`roll`, `simulate_scan(...)` →
  threshold → `read_answers` recovers EXACTLY `marked`; `read_roll` recovers `roll`. Test clean fills,
  a double-mark (flagged), a blank (blank), and (with a perspective transform → warp first) that reads
  still recover the answers after un-warping. Commit `feat(scan): roll + answer reading (fill-ratio + hysteresis)`.

## Task 5: Grading + stitch + pipeline orchestrator (TDD — end-to-end round-trip)
- [ ] `backend/omr/scan/grade.py`: `grade_sheet(omr_sheet, page_reads) -> result dict` — assemble all
  pages' reads, map detected printed labels through `omr_sheet.answer_key` per `q_pos`, compare to the
  correct set, apply the test's MarkingScheme → score/max_score/correct/wrong/blank + per-question
  {q_pos, marked, is_correct, flagged}.
- [ ] `backend/omr/scan/pipeline.py`: `process_image(image, resolve_sheet) -> page_result` runs
  decode_qr → (no QR → flag) → load sheet via `resolve_sheet(sheet_code)` → detect_fiducials → (none →
  alignment flag) → warp → threshold → read_roll (page 1) + read_answers → return the page read + flags.
  `process_scan_job(job)`: runs process_image on the job's image, stores the ScanJob status/confidence,
  attaches reads to the OmrSheet; when all pages of a sheet are present, calls grade_sheet, creates the
  `StudentResult` + `QuestionResponse`s + any `ReviewItem`s, sets `assembly_status=complete`.
- [ ] **END-TO-END round-trip test:** build a real Test (questions/options w/ known correct answers) +
  generate an OmrSheet (Phase-3 flow) + simulate a scan where the student marks the CORRECT answers →
  full pipeline → `StudentResult.score == max_score`, all `QuestionResponse.is_correct`. Then a sheet
  with some WRONG answers → score reflects the MarkingScheme. Then a double-marked question → a
  `ReviewItem(double_mark)` + `needs_review`. Commit `feat(scan): grading + stitch + pipeline orchestrator`.

## Task 6: Upload/scan endpoint + progress + review queue (TDD)
- [ ] `POST /api/v1/omr/scan/` multipart: `test` + one or more `files` (images and/or a multi-page PDF).
  Validate test belongs to user. Create a `ScanBatch`; for each file (PDF → split pages via fitz) create
  a `ScanJob` (status queued), then EAGERLY `process_scan_job` each (dev sync). Update batch
  processed/total. Return 201 `{batch_id, total}`.
- [ ] `GET /api/v1/omr/scan-batches/{id}/` → progress `{status, total, processed}` (client polls).
- [ ] `GET /api/v1/results/?test=` → StudentResults (child-scoped). `GET /api/v1/review/?test=` → open
  ReviewItems (with the cropped issue region optional/deferred). `POST /api/v1/review/{id}/resolve/`
  `{marked_options}` → corrects the QuestionResponse, recomputes the StudentResult, sets resolved.
- [ ] Tests: upload a simulated scan image → 201 + processed; results appear; a flagged read shows in the
  review queue; resolve recomputes. Cross-tenant test → 400. Commit `feat(scan): scan upload + progress + review queue endpoints`.

## Task 7: Frontend — scan + results + review
- [ ] `src/api/scan.js`; `routes/Scan.jsx` (pick test, upload files, poll progress bar via shadcn
  Progress, show summary); `routes/Results.jsx` (per-test StudentResult table + per-question drill-down,
  needs-review badge); `routes/ReviewQueue.jsx` (flagged items, a control to set the correct mark →
  resolve). Custom components only; build clean. Commit `feat(scan): scan upload + results + review UI`.

## Task 8: Phase 4 wrap-up + review + merge
- [ ] Full backend suite + check + frontend build; visual spot-check (simulate a scan, run pipeline,
  eyeball the warped image). Review (round-trip correctness, review-queue flagging, scope). Memory;
  merge `phase-4` → `main`.

## Self-review
- Coverage: scan/result models ✓(T1); simulator ✓(T2); align/QR/fiducial/warp ✓(T3); roll+answer read
  ✓(T4); grade+stitch+pipeline + end-to-end round-trip ✓(T5); endpoints+review ✓(T6); UI ✓(T7).
- The synthetic round-trip (generate→fill→scan→grade) is the correctness backbone — every CV stage is
  asserted against known-marked answers. Low-confidence → review queue, never guessed (per spec).
- Deferred: Celery+Redis async (dev = eager); cropped review-region images; threshold calibration vs
  real photos (synthetic fixtures approximate; tune against real scans in hardening).
