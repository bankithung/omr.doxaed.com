# OMRFlow — Multi-Mode OMR Creation + Advanced Features

**Spec date:** 2026-06-18
**Status:** Proposed (architecture + phased roadmap)
**Author:** synthesis from format research, advanced-feature research, and codebase audit
**Scope:** Test-creation modes (A/B/C/D + varieties), template/mode system, data-model
changes, generator + scanner extensions, the per-test and per-student Analytical Profile,
and a value-ordered phased roadmap where every phase is independently shippable end-to-end.

---

## 0. Grounding — what exists today (audit summary)

The current system is **Archetype 4 already, half-built**: a single procedural template, a
globally-unique per-sheet QR (`sheet_code`), and per-sheet stored shuffle + `answer_key`.

| Concern | Current implementation | File |
|---|---|---|
| Geometry | One procedural A4@100DPI template via `build_template(num_questions, num_options, roll_digits)` returning a descriptor dict (`page_px`, `fiducials`, `roll_grid`, `qr`, `answer_bubbles`, `page_count`, `page_map`). All layout from module constants. | `backend/omr/geometry.py` |
| Sheet code | `make_sheet_code(test_id, seed)` → `"{test_id:06d}-{token}"`, token = base32(sha256). Embeds test_id; no series. | `backend/omr/codes.py` |
| Shuffle | `build_sheet_plan(questions, seed, shuffle_q, shuffle_o)` → `question_order`, `option_order`, `answer_key` keyed by printed position. | `backend/omr/shuffle.py` |
| Generation | `GenerateView.post` builds ONE descriptor for the whole test, loops students, `seed=_derive_seed(test_id, student_id)`, one PDF per student, merges to batch PDF. `OmrSheet` is `update_or_create`-d per `(test, student)`. | `backend/omr/views.py` |
| Render | `render_sheet_pdf(sheet, descriptor)`. Draws fiducials, QR (`payload=f"{sheet_code}|{page+1}|{total}"`), header, roll grid (outlines only), answer bubbles. | `backend/omr/generator.py` |
| QR decode | `decode_qr` splits payload on `\|`, **requires exactly 3 parts**. | `backend/omr/scan/align.py` |
| Read | `to_binary` (global Otsu), `bubble_fill_ratio` (inner disc r*0.6), `classify` (hysteresis 0.45/0.20), `read_roll` (assumes rows 0–9, "exactly one filled"), `read_answers` (accepts `multiple_allowed`). | `backend/omr/scan/read.py` |
| Pipeline | `process_image` → decode QR → fiducials → warp → binary → read_roll (page 0) → read_answers. `process_scan_job` resolves `OmrSheet` by `sheet_code` + `test`; **identity is QR-only — the read roll is never reconciled to a Student**. `_maybe_grade` aggregates pages, calls `grade_sheet`, writes `StudentResult` (keyed `update_or_create` on `omr_sheet`) + `QuestionResponse` + `ReviewItem`. | `backend/omr/scan/pipeline.py` |
| Grade | `grade_sheet(omr_sheet, aggregated_reads)` uses `test.marking_scheme` (single `OneToOne`), falls back to 1/0. Floors score at 0. | `backend/omr/scan/grade.py` |
| Models | `OmrSheet` already stores `template_descriptor`, `page_map`, `answer_key`, `question_order`, `option_order` per sheet → **scanner is template-agnostic at read time**. `Test`, `MarkingScheme(OneToOne)`, `Question(topic, difficulty, order_index)`, `Option(label, is_correct)`, `Student(roll_number CharField(32), full_name encrypted)`. | `backend/{omr,assessments,rosters,results}/models.py` |
| Analytics | `analytics/services.py`: `test_summary` (avg/median/min/max, 5 buckets, top-5, hardest by wrong_rate, option_distribution via `_printed_to_original`), `student_detail` (topic_accuracy), `improvement` (retest chain). **No percentile/rank, no discrimination/point-biserial/KR-20, no sections, no persisted profile.** | `backend/analytics/services.py` |
| Frontend | `TestWizard.jsx` (mode-selection home), `Scan.jsx`, `Results.jsx`, `Analytics.jsx`, `StudentDetail.jsx`, `ReviewQueue.jsx`. Tailwind v4 + shadcn, custom components only. | `frontend/src/routes/` |
| Tests | `tests_omr.py` (38KB), `tests_scan.py` (98KB), `tests_analytics.py` (55KB) encode current single-template behavior — must be **extended, not loosened**. | `backend/{omr,analytics}/tests_*.py` |

**Three structural questions every OMR template answers** (from research): (1) how the
CANDIDATE is identified, (2) how the KEY/VERSION is identified, (3) how each ANSWER is read
and weighted. The mode system below is organized around exactly these three axes.

---

## 1. Template / Mode system

### 1.1 Design principle

Keep the **descriptor contract stable** so the scanner stays template-agnostic at read time
(it already reads geometry purely from `OmrSheet.template_descriptor`). Introduce a
`TemplateSpec` that resolves named modes/presets to a constant-set, and have
`build_template(spec)` emit the same descriptor shape **plus new optional sub-blocks** that
both generator and reader opt into via `descriptor.get(...)`. Old sheets keep working because
new blocks are absent and code branches defensively. This is the single most important
backward-compatibility rule.

`build_template` signature evolves to:

```python
build_template(spec: TemplateSpec) -> descriptor   # spec carries num_questions, num_options,
                                                     # roll spec, sections, series, page size,
                                                     # columns, radii, integrity marks, qr_version
```

A thin compatibility shim `build_template(num_questions, num_options, roll_digits)` is kept
(delegates to a default Standard spec) so existing tests pass unchanged.

### 1.2 New descriptor sub-blocks (all optional; absence = legacy behavior)

- `roll_grid.kind`: `"writein"` (current; candidate-bubbled) | `"prebubbled"` (Mode B) | `"none"`.
- `roll_grid.charset`: `"digits"` (default 0–9) | `"alnum"` (A–Z0–9) — generalizes `read_roll`.
- `roll_grid.prefilled`: bool — when true, generator draws solid discs at the assigned value.
- `series_grid`: `{origin, col_pitch, row_pitch, radius, charset:[A,B,C,D], kind:"writein"|"prebubbled"}`.
- `sections`: `[{key, label, q_start, q_pos_range:[lo,hi], policy:{type:"all"|"choose_k", k:int}, marking_ref}]`.
- `answer_bubbles[i].section`: section key tag per question (for sectional analytics).
- `answer_bubbles[i].kind`: `"mcq"` (default) | `"msq"` | `"numeric"` — answer-region type (Archetype 3).
- `numeric_grids`: `[{q_pos, origin, col_pitch, row_pitch, radius, cols, rows, has_sign, has_decimal}]`.
- `integrity`: `{signature_box:bool, thumb_box:bool, gating_fields:[...]}`.
- `barcode`: `{x, y, w, h, symbology:"code128"}` — redundant sheet-code encoding.
- `qr_version`: int (payload schema version; see §4.1).

### 1.3 The modes

| Key | Name | Candidate ID | Version/Key ID | Answer reading | Grading | Maps to archetype |
|---|---|---|---|---|---|---|
| `standard` | **A — Standard** | write-in roll grid (current) | per-sheet QR (current) | MCQ single-bubble | per-sheet `answer_key` | 4 (base) |
| `roster_prebubbled` | **B — Roster, pre-bubbled roll** | **pre-bubbled** roll (auto-marked from `Student.roll_number`); QR is the true identity | per-sheet QR | MCQ single-bubble | per-sheet `answer_key`; **roll↔QR reconciliation** | 4 + pre-print |
| `competitive` | **C — Competitive (NEET/UPSC)** | candidate-bubbled roll grid (+ optional pre-bubble); printed series code | **booklet/series** (shared key per series) + per-sheet QR | MCQ 4/5-option; sections; optional N-of-M | per-section marking + fractional/flat negative; sectional cutoffs | 1 + 2 |
| `mixed_types` | **D1 — Mixed answer types (JEE/GATE)** | candidate-bubbled roll grid | per-sheet QR or series | MCQ + **MSQ** (exact-subset) + **numeric grid-in** (value/range) | per-type weights & negatives | 3 |
| `data_capture` | **D2 — Data-capture / award sheet (CBSE-style)** | roll grid rows | n/a (no key) | marks-grid capture; bubble+box override | record values, no key-grading | CBSE award |
| `survey` | **D3 — Survey / practice** | optional/none | per-sheet QR | MCQ, no key or self-key | feedback only, no scoring | 4 (degenerate) |

**Build order of modes (by value × specificity):** B → C → D1 → D2/D3. A is already shipped.

### 1.4 Per-mode mechanics

**Mode A — Standard (already live).** No change required; becomes `mode="standard"` default.
write-in roll, per-sheet QR, MCQ, single `MarkingScheme`.

**Mode B — Roster with pre-bubbled roll + per-student shuffle.**
- *Layout:* identical to Standard, but the roll grid is rendered with the candidate's roll
  digits **filled solid** (one disc per digit-column at the matching row).
- *Roll handling:* pre-bubbled. `roll_grid.kind="prebubbled"`, `roll_grid.prefilled=True`,
  and the sheet dict carries `roll_value`. Generator draws solid discs (currently it only draws
  outlines via `c.circle(..., fill=0)` — add a `fill=1` pass for assigned digits).
- *Sets/series:* none — every student gets their own per-student shuffle (existing
  `seed=_derive_seed(test, student)` model). The QR is the identity.
- *Identification:* QR resolves the `OmrSheet` → `student` (unchanged). The pre-bubbled roll is
  **read as a cross-check**: `read_roll` runs verify-only against `omr_sheet.student.roll_number`;
  a mismatch raises a new `roll_mismatch` review reason (tamper-evidence). This is the headline
  differentiator — automatic, tamper-evident student identification.
- *Grading:* unchanged (per-sheet `answer_key`).

**Mode C — Competitive (NEET / UPSC-style booklet series).**
- *Layout:* named **sections** with section headers; 4 or 5 options; printed
  human-visible **Test Booklet Code** A/B/C/D bubble group; optional candidate-bubbled roll
  grid; optional integrity marks (signature/thumb boxes). High-density preset (3-col / both
  sides) for 180–200Q papers.
- *Roll handling:* candidate-bubbled by default (matches real exams); pre-bubble optional for
  coaching mocks (reuses Mode B mechanism).
- *Sets/series:* **shared shuffle per series.** One printed booklet variant (Set A) → one
  `answer_key` shared by all students who hold Set A. This is a *different* seed model:
  `seed = derive(test_id, series_code)` instead of `(test_id, student_id)`. A new `OmrSeries`
  row stores `{series_code, seed, question_order, option_order, answer_key, template_descriptor,
  page_map}`; each `OmrSheet` references its series for the key. The QR still disambiguates the
  exact sheet, and the series code is carried in the QR payload as redundancy and for the
  shared-booklet case (one student may be handed any booklet).
- *Optional-question logic:* a section with `policy={type:"choose_k", k:10}` over `M=15`
  questions grades **only the first K attempted** (NEET Section B rule) — see §5 grading.
- *Identification:* QR → exact sheet (and thus series → key). The printed series bubble is read
  via new `read_series()` as a cross-check / fallback when the QR is unreadable; a series-vs-QR
  conflict raises `series_unreadable` / `series_mismatch`.
- *Grading:* per-section marking schemes (e.g. +4/−1 MCQ, fractional 1/3 for UPSC, flat −1 for
  NEET, −0.5 for SSC), optional-N-of-M, sectional subtotals + qualifying cutoffs, optional
  cross-series normalization.

**Mode D1 — Mixed answer types (JEE Main / GATE).**
- *Numeric grid-in:* `answer_bubbles[i].kind="numeric"` + a `numeric_grids[i]` block (multi-column
  0–9 plus optional sign/decimal rows). New `read_numeric_grid()` assembles a number string;
  `grade_sheet` matches by value/range with tolerance, usually no negative.
- *MSQ (multi-select):* `kind="msq"` reuses `read_answers(multiple_allowed=True)`; grading is
  **exact-subset all-or-nothing**, no partial, no negative (GATE rule).
- *Per-question weights:* `Question.marks`/`negative` per item (1 vs 2 mark) drive grading.

**Mode D2 — Data-capture / award (CBSE-style).** Roll rows × marks columns; bubble + write-in
box with **box-overrides-bubble** precedence (needs light OCR/ICR on the box — deferred, see
open questions). No answer key; capture values only.

**Mode D3 — Survey / practice.** MCQ with no scoring or self-revealed key; feedback only.

---

## 2. Data-model changes (backward compatible)

All new fields are nullable / defaulted so existing rows and tests are unaffected. New tables
are additive. The denormalized `OmrSheet.template_descriptor` means **old sheets keep their
exact shape**; only sheets generated after the change carry new descriptor blocks.

**`assessments.Test`** (additions)
- `mode = CharField(choices=[standard, roster_prebubbled, competitive, mixed_types, data_capture, survey], default="standard")`
- `template_spec = JSONField(default=dict)` — resolved/edited `TemplateSpec` (page size, columns, options, integrity marks, qr_version).
- `default_options = PositiveSmallIntegerField(default=4)` — 4 vs 5 default per test.

**NEW `assessments.Section`** (Mode C/D)
- `test (FK)`, `key`, `label`, `order_index`, `q_pos_start`, `q_pos_end` (or M2M membership),
  `policy_type ("all"|"choose_k")`, `choose_k (int null)`.

**`assessments.MarkingScheme`** → keep the `OneToOne` for backward compat; add **NEW
`assessments.SectionMarkingScheme`** `{section (FK), marks_per_correct, negative_marks_per_wrong,
partial_marking, multiple_correct_allowed, scheme_kind ("mcq"|"msq"|"numeric"), qualify_pct (null)}`.
`grade_sheet` resolves per-section scheme, falling back to the test-level `MarkingScheme`.

**`assessments.Question`** (additions)
- `section = FK(Section, null=True)`
- `kind = CharField(choices=[mcq, msq, numeric], default="mcq")`
- `marks = DecimalField(default=1)`, `negative_marks = DecimalField(default=0)` (per-item override)
- `numeric_answer = JSONField(null=True)` — `{value, tolerance, min, max}` for numeric items.

**`omr.OmrSheet`** (additions)
- `mode = CharField(default="per_student")` — `per_student` | `booklet_series`.
- `series = FK("omr.OmrSeries", null=True)` — set in booklet mode; key comes from series.
- `roll_kind = CharField(default="writein")` — `writein` | `prebubbled` | `none`.
- `roll_value = CharField(blank=True)` — the pre-bubbled digit string (Mode B).
(All other per-sheet fields already exist.)

**NEW `omr.OmrSeries`** (Mode C)
- `test (FK)`, `series_code (A/B/C/D/…)`, `seed`, `question_order`, `option_order`, `answer_key`,
  `template_descriptor`, `page_map`, `page_count`. `unique_together (test, series_code)`.
  `OmrSheet.series` → this; decouples the key from per-student sheets.

**NEW `omr.OmrTemplate`** (optional, Phase 2+) — named, versioned layout presets
(`page_size, columns_per_page, rows_per_col, num_options, option_pitch, radii, roll charset/rows,
has_series_grid, has_section_headers, qr_payload_version`). Referenced by `Test`. Until this
lands, `Test.template_spec` JSON is the spec source.

**`results.ReviewItem.REASON_*`** (additions)
- `roll_mismatch`, `series_unreadable`, `series_mismatch`, `numeric_unreadable`.

**`results.QuestionResponse`** (additions)
- `section = FK(Section, null=True)` (or derive via `question.section`) for sectional reports.
- `numeric_value = CharField(blank=True)` for numeric grid-in reads.

**NEW `analytics.TestProfile`** (one-to-one per Test) + **`analytics.StudentProfile`**
(per student across attempts) — persisted, Celery-populated analytical profiles (see §5.4).

**Scope rule:** every new owner-scoped table follows the existing owner XOR org isolation;
child tables (Section, OmrSeries, SectionMarkingScheme) scope through their parent Test.

---

## 3. Generator changes

`render_sheet_pdf(sheet, descriptor)` already consumes the descriptor generically. Changes are
**additive draw passes gated on descriptor blocks**:

1. **Pre-bubbled roll (Mode B) — `_draw_roll_grid`.** Today it draws only outlines. Add:
   when `roll_grid.get("prefilled")` and `sheet.get("roll_value")`, for each digit-column draw a
   **solid filled disc** (`c.circle(cx, cy, r, fill=1, stroke=1)`) at `row == int(digit)`, plus
   the outline ring for the rest. Make discs slightly inset (draw at `r` but the reader samples
   `r*0.6`, so a full fill reads ≈1.0). Tune so machine-printed discs land well above `FILL_HIGH`.

2. **Series code grid — NEW `_draw_series_grid`.** Driven by `descriptor["series_grid"]`. Draws a
   small A/B/C/D bubble group (write-in) or pre-filled disc (when the booklet's series is fixed).
   Human-readable "Test Booklet Code: A" label printed alongside.

3. **Section headers — NEW `_draw_section_headers`.** Driven by `descriptor["sections"]`; prints
   "Section A — Physics (Q1–35, all)" / "Section B (attempt any 10 of 15)" bands above the
   relevant answer rows.

4. **Numeric grids — NEW `_draw_numeric_grid`.** Driven by `descriptor["numeric_grids"]`; draws a
   digit-box header + 0–9 bubble columns (+ optional sign/decimal rows) for grid-in items.

5. **QR payload builder (the one place to extend) — `_draw_qr`.** Replace the hardcoded
   `f"{sheet_code}|{page+1}|{total}"` with a **versioned, forward-compatible** payload
   (see §4.1). This is the single highest-blast-radius change — version it.

6. **Integrity / branding overlays (cheap, additive).** Signature box, thumb-impression box,
   Code-128 **barcode** redundancy of `sheet_code` (pyzbar already decodes it), org **logo /
   brand color / watermark** (faint diagonal `student name + sheet_code` — doubles as anti-leak
   marking). All pure ReportLab overlays gated on descriptor/sheet flags.

7. **Page size + density presets.** Parameterize `W/H` and columns from the spec instead of
   module constants, so 3-column / both-sides / Letter layouts become presets. Re-validate the
   geometry asserts per preset (fit checks for roll grid, QR quiet zone, fiducial clearance).

**Generation flow (`GenerateView`) changes.**
- Resolve `Test.mode` → choose seed model: per-student (A/B/D) vs per-series (C).
- Mode C: build/fetch `OmrSeries` rows (one shuffle per series), then assign each student a
  series (round-robin or chosen), render the booklet, and create `OmrSheet` rows referencing
  the series. Update `StudentResult` de-dup to remain keyed on `omr_sheet` (already is).
- Mode B: set `roll_kind="prebubbled"`, `roll_value=student.roll_number`, pass `prefilled=True`
  into the spec; descriptor gains `roll_grid.prefilled`.
- Keep the idempotent `update_or_create` per `(test, student)` (or per `(series)` for shared
  booklets) so re-generation never 500s on the unique `sheet_code`.

---

## 4. Scanner changes

The scanner stays descriptor-driven; changes are localized to QR parsing, roll reliability, and
new read functions.

### 4.1 QR / sheet-code: always know which TEST + KEY (the explicit requirement)

- **Versioned payload.** New format (qr_version ≥ 2), forward-compatible:
  `"v2|{sheet_code}|{page}|{total}|series={S}|tpl={V}"` — or a compact `k=v` tail. `sheet_code`
  already embeds `test_id` (`{test_id:06d}-…`), so **the test is always recoverable from the QR
  alone**; series and template version are appended.
- **`decode_qr` becomes tolerant:** parse a leading version token; for `v2+`, read the first 4
  positional fields and then any `key=value` trailers (ignore unknown keys). For legacy 3-field
  payloads (no version prefix), keep the current path. This removes the brittle
  "exactly 3 parts" contract without breaking old sheets.
- **Identity resolution (`process_scan_job`):** unchanged primary path —
  `OmrSheet.objects.get(sheet_code=sheet_code, test=job.batch.test)` → resolves test, student,
  `answer_key`, descriptor, page. For Mode C, resolve the **key from `omr_sheet.series`** (or
  from the parsed `series=` field when a booklet is shared and the sheet row is the booklet, not
  the student). Redundant barcode decode is a fallback when the QR is torn.

### 4.2 Pre-bubbled roll, read reliably (Mode B)

- Pre-bubbled discs are physically identical to hand-filled ones, so **existing `read_roll`
  already detects them** (`simulate.py` fills roll bubbles this way). Make it **verify-only**:
  compare the read digit string to `omr_sheet.student.roll_number`; on mismatch set flag
  `roll_mismatch` (new `ReviewItem` reason) rather than trusting OCR. Identity still comes from
  the QR, so a wrong read never silently mis-identifies a student.
- Robustness for machine-printed fills: optionally raise `FILL_HIGH` for prebubbled columns,
  and/or normalize fill ratio against a couple of template reference discs (handles scan
  exposure variance). Keep the inner-disc `r*0.6` sampling (already mitigates ring-only fills).
- Generalize `read_roll` to a **charset** (digits 0–9 today; A–Z0–9 for alphanumeric/booklet
  rolls): return `row → label` from `roll_grid.charset` instead of hardcoding `str(row)`.

### 4.3 New read functions

- **`read_series(binary, descriptor)`** → `(series_label, flag)`; reuses the roll reader over the
  `series_grid` block. Conflict with QR-resolved series → `series_mismatch`.
- **`read_numeric_grid(binary, descriptor, q_pos)`** → assembled number string (+ `numeric_unreadable`
  flag) for Mode D1 grid-in items.
- **MSQ:** plumb `multiple_allowed` from the descriptor/section into `read_answers` per question
  (it already accepts the arg; today `process_image` hardcodes the default).

### 4.4 CV hardening (mobile / lighting — Phase 6)

- Replace single global Otsu with **adaptive (per-region) thresholding** so phone photos under
  uneven light grade reliably.
- Strengthen `detect_fiducials` for denser layouts (extra registration marks / timing track in
  the spec); keep area heuristics scaled by `W/CANON_W` but widen tolerances per preset.
- **Mobile camera capture** (React): device-camera flow with fiducial-framing guidance, then
  upload into the existing `warp_to_canonical` pipeline (already tolerates perspective).

### 4.5 Grading integration

- `grade_sheet` resolves **per-section** scheme (new `SectionMarkingScheme`), falling back to the
  test-level `MarkingScheme` (keeps current behavior for Mode A). Adds:
  - fractional negatives (UPSC 1/3, GATE −1/3 & −2/3, SSC −0.5) and flat (NEET −1) via Decimal;
  - **optional N-of-M**: within a `choose_k` section, grade only the first K attempted (by q_pos
    order) — un-attempted-beyond-K ignored;
  - **MSQ** exact-subset all-or-nothing (no partial, no negative);
  - **numeric** value/range match with tolerance;
  - **sectional subtotals + qualifying cutoffs** (e.g. CSAT 33% qualifying-only);
  - **answer-key correction / bulk re-grade**: a versioned key with bonus/drop/changed-key flags
    consumed by `grade_sheet` and a re-grade path that re-scores all scanned sheets **without
    re-scanning** (audit-logged). High operational value, clear differentiator.

---

## 5. Analytical Profile (per test AND per student)

The user's literal requirement: *every created test becomes a proper analytical profile.* Make
it a **first-class persisted artifact**, not an on-demand view. All formulas are pure aggregation
over `StudentResult` / `QuestionResponse` (numpy already present via OpenCV) — no new heavy deps.

### 5.1 Per-test profile (`analytics.TestProfile`, 1:1 with Test)

Populated by a Celery task fired when a `ScanBatch` finishes grading (Celery already wired;
eager in dev). Contents:

- **Score stats:** distribution (extend beyond 5 fixed buckets to a configurable histogram),
  mean, median, **stddev / z-score**, min/max.
- **Percentile + rank table:** each student's percentile (% scoring ≤ them) + overall rank.
- **Item analysis per question:**
  - *Difficulty index (p-value)* = correct / n.
  - *Discrimination index* = upper-27% group correct-rate − lower-27% group correct-rate.
  - *Point-biserial correlation* of item-correct vs total score.
  - *KR-20* reliability for the whole test.
  - **Automatic flags:** too-easy / too-hard, **negative discrimination**, **miskey-suspect**.
- **Distractor effectiveness:** per wrong option, selection frequency split by **ability tertile**
  (extends the existing `_printed_to_original` mapping + `option_distribution`). Flags
  non-functioning distractors and items chosen more by high scorers (miskey signal).
- **Sectional (Mode C):** per-section subtotals, averages, accuracy, sectional cutoffs /
  qualification counts, per-section toppers.
- **Cross-series normalization (Mode C, later):** mean-sigma (z) equating across booklet series,
  with an IRT/Rasch hook reserved (the marquee psychometric differentiator, matching NTA-style
  normalization).

### 5.2 Per-student profile (`analytics.StudentProfile`, spanning attempts)

- Percentile, overall rank, normalized/scaled score within the cohort.
- **Section + topic strengths-weaknesses** (radar/heatmap), strong/weak tags, suggested focus.
- **Distractor-aware mistake list** (which wrong option, how common it was).
- **Improvement trajectory** across retests (`Test.parent_test` / `attempt_number` already model
  this; extend the existing `improvement()` into a persistent longitudinal profile).

### 5.3 Deliverables

- **Branded downloadable PDF report card per student** (score, rank, percentile, sectional
  breakdown, topic profile, distractor-aware mistakes, improvement vs last attempt) — reuses the
  ReportLab pipeline and existing CSV/Excel/PDF export. This is the tangible paid deliverable.
- **Per-test psychometric report** (item-analysis table + reliability + flagged items).
- New analytics endpoints + export columns; old endpoints unchanged.

### 5.4 Sequencing within analytics (value-to-effort)

Item analysis + distractor analysis + percentile/rank + report card **first** (immediate wow,
low risk, pure functions). Then sectional/cutoff logic for Mode C. Then cross-series
normalization **last** (highest effort, highest prestige).

---

## 6. Phased roadmap (each phase independently shippable + verifiable)

Ordered by value × dependency. **Every phase ships UI + API + generation/scanning/analytics as
relevant + backend tests + cross-browser E2E**, and leaves the product fully working.

### Phase 1 — Mode scaffold + Mode B (pre-bubbled roll) — *clearest high-value slice*
- **Goal:** Multi-mode foundation + the most concretely-specified mode end-to-end.
- **Deliverables:** `Test.mode` + `template_spec` fields (+ migration, default `standard` →
  zero behavior change for existing tests); `TemplateSpec` + `build_template(spec)` with the
  Standard shim; descriptor `roll_grid.kind/prefilled`; generator solid-disc roll rendering;
  versioned QR payload (`v2`) + tolerant `decode_qr` (legacy still parses); verify-only
  `read_roll` reconciliation with new `roll_mismatch` review reason; `OmrSheet.roll_kind/roll_value`;
  `TestWizard.jsx` mode picker (A vs B) + roster selection for B.
- **Verify:** unit tests (spec→descriptor; prefilled disc reads ≥ FILL_HIGH; QR v2 round-trip;
  legacy QR still decodes; roll-match passes / mismatch flags). E2E: create Mode B test →
  generate → printed roll is pre-filled → scan → student auto-identified via QR → roll
  cross-check green → result graded. Existing `tests_omr`/`tests_scan` still pass unchanged.

### Phase 2 — Configurable marking + analytics core (item analysis, percentile, report card)
- **Goal:** "Every test → a proper analytical profile" for the modes that exist (A, B).
- **Deliverables:** `analytics.TestProfile` + `StudentProfile` models + Celery populate task;
  item analysis (p-value, upper-lower discrimination, point-biserial, KR-20), distractor
  effectiveness by tertile, percentile + rank; branded per-student **PDF report card**; new
  analytics endpoints + export columns; `Analytics.jsx` / `StudentDetail.jsx` surfacing.
  Configurable negative marking surfaced in the wizard (validated end-to-end; engine already
  supports a single scheme).
- **Verify:** golden-number unit tests for each psychometric formula (known fixtures);
  profile auto-generates after a scan batch completes; report-card PDF downloads. E2E: scan a
  cohort → open the test profile (flagged items visible) → download a student report card.

### Phase 3 — Mode C foundation: sections + per-section marking + sectional analytics
- **Goal:** NEET/UPSC structure without full booklet equating yet.
- **Deliverables:** `Section` + `SectionMarkingScheme` models; descriptor `sections` + section
  headers in generator; section-tagged `QuestionResponse`; `grade_sheet` per-section marking +
  fractional/flat negatives + sectional subtotals + qualifying cutoffs; optional **N-of-M**
  (choose-k) grading; 4 vs 5 options surfaced per test; sectional profile (per-section toppers,
  cutoffs) in the analytics. Wizard gains section builder.
- **Verify:** grading unit tests for fractional negatives, choose-k (only first K graded),
  sectional cutoffs/qualification. E2E: build a 2-section test (one choose-k) → generate → scan
  → sectional subtotals + qualification appear in the profile.

### Phase 4 — Mode C booklet series (shared keys) + answer-key correction / bulk re-grade
- **Goal:** True NEET/UPSC booklet-series mode + the operational re-grade differentiator.
- **Deliverables:** `OmrSeries` model + per-series seed/shuffle/key; `OmrSheet.series`;
  printed series-code grid + `_draw_series_grid`; `read_series()` + QR `series=` field +
  `series_mismatch` review reason; pipeline resolves key from series; **answer-key correction**
  (versioned key, bonus/drop/changed-key) + **bulk re-grade without re-scanning**, audit-logged.
- **Verify:** unit tests (all students of series A share one key; series read matches QR; re-grade
  rescores every sheet, audit entries written). E2E: generate Sets A–D → scan a mix → grade
  against the correct per-series key → mark a question bonus → bulk re-grade updates all scores.

### Phase 5 — Mode D1: mixed answer types (numeric grid-in + MSQ)
- **Goal:** JEE/GATE answer regions beyond single-bubble MCQ.
- **Deliverables:** `Question.kind` (mcq/msq/numeric) + `numeric_answer` + per-item `marks`/`negative`;
  descriptor `numeric_grids` + `answer_bubbles[].kind`; `_draw_numeric_grid`; `read_numeric_grid`;
  MSQ exact-subset grading; numeric value/range grading; `numeric_unreadable` review reason.
- **Verify:** unit tests (numeric grid reads "12.5" and matches with tolerance; MSQ all-or-nothing;
  per-type weights). E2E: build a mixed test (MCQ + numeric + MSQ) → generate → scan → each type
  graded by its own rule.

### Phase 6 — Scan robustness + mobile capture + live review UI
- **Goal:** Remove the scanner-hardware barrier; harden accuracy.
- **Deliverables:** adaptive per-region thresholding; skew/rotation/lighting hardening; **mobile
  camera capture** flow with fiducial framing; **live review queue** (warped crop + detected-mark
  overlay + keyboard-fast adjudication) writing every decision to the audit log; bulk multi-page
  PDF / ZIP fan-out via Celery; Code-128 barcode redundancy.
- **Verify:** CV regression tests on noisy/rotated fixtures; review-decision audit entries. E2E
  (cross-browser): phone-style photo upload → aligns and grades; low-confidence read → review
  UI → human confirms → result updates.

### Phase 7 — Cross-series normalization + longitudinal profiles + extra varieties (D2/D3)
- **Goal:** Marquee psychometric credibility + remaining varieties.
- **Deliverables:** mean-sigma (z) equating across booklet series (IRT/Rasch hook reserved);
  persistent per-student longitudinal `StudentProfile` across all tests; cohort/class/batch
  comparison; Mode D2 (data-capture/award, box-overrides-bubble — OCR scoped per open question)
  and Mode D3 (survey/practice); deterministic tie-breaking rules; per-student watermark / anti-leak.
- **Verify:** normalization unit tests (known distributions → expected scaled scores); longitudinal
  profile spans attempts. E2E: multi-series test → normalized scores in the profile; survey mode
  collects responses with no scoring.

**Dependency notes:** P1 unblocks everything (mode scaffold + QR versioning). P2 is independent
of P3+ (works on A/B). P3 precedes P4 (sections before booklet equating) and P7 (normalization
needs series from P4). P5 is independent. P6 is independent and can be pulled earlier if mobile
adoption is the priority.

---

## 7. Open questions for the product owner (short, high-leverage)

1. **Which competitive archetype to mirror first in Mode C — NEET (flat −1, optional N-of-M,
   thumb/dual-signature) or UPSC (clean 4-set A/B/C/D, fractional 1/3, qualifying CSAT)?** This
   sets the Phase 3/4 fidelity target.
2. **Default options: 4 or 5?** UPSC commonly uses 5; most others 4. Drives the wizard default
   and template presets.
3. **Paper size + density default: A4 only, or add Letter and a high-density 3-column / both-sides
   preset for 180–200Q papers?** Affects geometry parameterization scope.
4. **How strict must NEET/UPSC fidelity be** — faithful integrity marks (thumb impression,
   dual signatures, gating-field "zero if blank") and dual-code (letter set + numeric booklet
   serial), or a "competitive-style" approximation? Determines how much integrity/gating work
   lands in Phase 3/4 vs later.
5. **CBSE-style write-in-box override (Mode D2) — in scope?** It requires light OCR/ICR on the
   box (box-overrides-bubble), a new dependency class; if yes, schedule it explicitly in Phase 7.
6. **Mode C series assignment policy:** auto round-robin across the roster, or examiner-chosen
   per student/section? Changes the generation UX and `OmrSheet.series` assignment.
