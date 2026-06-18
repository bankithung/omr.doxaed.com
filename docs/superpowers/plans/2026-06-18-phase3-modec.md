# OMRFlow Phase 3 — Mode C "competitive" FOUNDATION (sections + per-section marking + sectional analytics)

**Plan date:** 2026-06-18
**Status:** Ready to build

> ## ⚠️ CRITIQUE CORRECTIONS — AUTHORITATIVE (override the body where they conflict)
> The adversarial review (NEEDS_REVISION) found three issues that MUST be implemented this way:
>
> **C1 — Choose-K = "BEST K of attempted", NOT "first K by printed position".** Sheets shuffle
> per-student (`shuffle.py` `rng.shuffle`), so "first K by printed q_pos" grades different canonical
> questions for different students — unfair + breaks cross-student comparability. Instead: among the
> ATTEMPTED questions in a choose_k section, grade the **K with the highest question_score** (rank by
> per-question score desc; tie-break by **canonical `Question.order_index` asc**, never printed q_pos).
> Surplus attempted (beyond K) → `status="ignored"`, score 0, no negative, excluded from
> counts/max_subtotal. Blanks never consume a slot. This is shuffle-INVARIANT. Golden test MUST run
> with `shuffle_questions=True` and prove two differently-shuffled sheets attempting the same canonical
> set grade an IDENTICAL subset.
>
> **C2 — Section headers must NOT move any answer-bubble coordinate.** The answer grid is rigid
> (2 cols × 25 rows = 50/page; row_pitch floored to 2R+4; no spare whitespace). Do NOT advance `cy` /
> insert inline gaps (that reflows pagination + breaks page_map). Draw section labels in EXISTING
> whitespace only (header/legend area at the top of the sheet + optional marker in the question-number
> gutter), purely as a generator draw pass keyed off each section's start. The Task-3B test
> "answer_bubbles cx/cy are byte-identical with vs without sections" MUST pass.
>
> **C3 — `retest()` must clone Sections.** Extend `assessments/views.py retest()` to deep-copy
> Section + SectionMarkingScheme (range survives since order_index is copied) and call
> `sync_question_membership()` on the clone. Add a test: a retest of a competitive test preserves
> sections, schemes, and choose-k. Otherwise a competitive retest silently degrades to standard.

**Scope (this phase ONLY):** named SECTIONS over a test's questions, PER-SECTION marking
(configurable flat e.g. NEET −1 OR fractional e.g. UPSC −1/3), optional N-of-M
("choose any K of M" — grade only the first K ATTEMPTED in source order), per-section
SUBTOTALS, qualifying CUTOFFS (e.g. CSAT 33% qualifying-only), section headers in the
generated sheet, 4-vs-5 options surfaced per test, and SECTIONAL analytics.
**Explicitly OUT OF SCOPE (later phases):** `OmrSeries` / booklet shared keys / `read_series`
/ series QR field / answer-key correction + bulk re-grade (Phase 4); `Question.kind` /
`Question.marks` / `Question.negative_marks` / `numeric_answer` / MSQ-grid / numeric grid-in
(Phase 5); cross-series normalization + IRT (Phase 7).
**Spec ref:** `docs/superpowers/specs/2026-06-18-omr-modes-and-advanced-features.md` §1.1–1.2,
§2, §3.3, §4.5, §5.1 "Sectional", Phase 3 in §6.

**Non-negotiable invariant (CLAUDE.md + spec §1.1):** a STANDARD test (no sections) must be
**bit-for-bit unchanged** — same grading numbers, same descriptor bytes, same analytics JSON.
Every new field is nullable/defaulted; every new code path is gated on section presence;
existing `tests_omr.py` / `tests_scan.py` / `tests_analytics.py` must pass **unchanged**
(extend, never loosen).

---

## 0. Grounding (verified against current code)

| Concern | Current state (file:line) | Phase-3 touch |
|---|---|---|
| Grading | `grade_sheet(omr_sheet, aggregated_reads)` is the whole algorithm — single `omr_sheet.test.marking_scheme` lookup in one `try/except` (`backend/omr/scan/grade.py:46-57`), `max_score = len(answer_key)*marks_per_correct` (`:59-60`), printed-q_pos loop (`:68-109`), whole-test floor `max(0,score)` (`:112`), flat return dict (`:114-121`). `flagged` always False here. | Per-section scheme RESOLVER + section loop tagging + choose-k pre-pass + subtotal/cutoff post-pass + additive return keys. |
| Persistence | `pipeline._maybe_grade` (`backend/omr/scan/pipeline.py:235-362`): aggregates done pages (`:282-295`), `grade_sheet` (`:297`), `StudentResult.update_or_create` keyed on `omr_sheet` (`:300-312`), wipes+recreates `QuestionResponse` (`:315,341-348`), `flagged` set HERE from job reads (`:328-333`), unpacks `pq["q_pos"/"marked"/"is_correct"/"flagged"]` (`:321-325`). | Stamp `QuestionResponse.section`, persist `StudentResult.section_breakdown`/`qualified_all`. DO NOT rename/reorder per_question keys. |
| Scheme model | `assessments.MarkingScheme` OneToOne→Test (`models.py:49-54`). | Keep unchanged = fallback/default. |
| Test | `Test.mode` (standard, roster_prebubbled), `Test.template_spec` JSON (`models.py:23-40`); migration `0003_mode_and_template_spec`. | Add `competitive` choice + `Test.default_options`. |
| Question | `Question(order_index, text, topic, difficulty)` (`models.py:57-66`); no section. | Add nullable `section` FK. |
| QuestionResponse | `(student_result, question(nullable), q_pos, marked_options, is_correct, flagged)` (`results/models.py:105-134`). | Add nullable `section` FK + index. |
| Geometry | `_answer_grid` 2col×25row=50/page; coords descriptor-driven; **sections do not exist**. `build_template(num_questions, num_options, roll_digits, roll_kind)` clamps `num_options=max(2,min(6,...))` (`geometry.py:77`). | Add `sections` descriptor block + `answer_bubbles[i].section`; reserve header gap; honor `default_options`. |
| Generator | `_draw_answer_bubbles` per page (`generator.py:226-271`); pre-bubbled solid-disc precedent (`:215-223`). | Add gated `_draw_section_headers`. |
| views.GenerateView | `num_options = max(2,min(6,max_options))` (`views.py:197-201`); `roll_kind` from mode (`:211-213`). | Honor `Test.default_options`. |
| Analytics | `TestProfile.profile` JSONField (`analytics/models.py:16-60`); `compute_test_profile(results_data)` (`psychometrics.py:391`), `build_results_data(test)` (`:555`). Pure-function style, `MIN_COHORT_FOR_PSYCHOMETRICS=10`. | Add `profile["sections"]`; optional arg to `compute_test_profile`; `section_scores` in `results_data`. |
| Latest migrations | assessments `0003`, results `0004_publicresultshare`, analytics `0001_initial_profiles`. | New: assessments `0004`, results `0005`, analytics `0002` (optional). |

**Two coordinate spaces (load-bearing).** CANONICAL DB order = `Question.order_index`
(authoring space — examiner says "Q1–35 = Physics"). PRINTED per-sheet order = `q_pos`, the
shuffled space used by `OmrSheet.question_order` (`list[Question.id]` in printed order),
`OmrSheet.answer_key` (`{str(q_pos):[labels]}`), `QuestionResponse.q_pos`, analytics
`item_scores`. Sections are AUTHORED in canonical space; grading/analytics run in PRINTED
space. **The bridge is `omr_sheet.question_order[q_pos] → Question.id → Question.section`.**
Choose-k "source order" is resolved in PRINTED `q_pos` order (the order bubbles appear on the
sheet) — decided deliberately in §2.3.

---

## 1. Models + migrations (additive, backward-compatible)

### 1.1 NEW `assessments.Section` (plain `models.Model`, scoped through Test)

```python
class Section(models.Model):
    POLICY_ALL = "all"
    POLICY_CHOOSE_K = "choose_k"
    POLICY_CHOICES = [(POLICY_ALL, "All"), (POLICY_CHOOSE_K, "Choose K")]

    test        = models.ForeignKey(Test, on_delete=models.CASCADE, related_name="sections")
    key         = models.CharField(max_length=16)         # stable short id "A","PHY"; unique per test
    label       = models.CharField(max_length=255)        # human "Physics","CSAT Paper II"
    order_index = models.PositiveIntegerField(default=0)   # display + grading order
    q_start     = models.PositiveIntegerField()            # inclusive, 1-based Question ordinal (canonical)
    q_end       = models.PositiveIntegerField()            # inclusive
    policy      = models.CharField(max_length=16, choices=POLICY_CHOICES, default=POLICY_ALL)
    choose_k    = models.PositiveIntegerField(null=True, blank=True)  # required iff policy=choose_k

    class Meta:
        ordering = ["order_index", "id"]
        constraints = [
            models.UniqueConstraint(fields=["test", "key"], name="uniq_section_test_key"),
        ]
```

**Membership = RANGE is source of truth** (`q_start..q_end` over `Question.order_index`,
1-based inclusive). Rationale: real competitive papers ARE contiguous ("Section A: Q1–35");
range makes overlap/coverage validation trivial; choose-k maps to a contiguous slice; section
header bands print ranges; no per-question write fan-out on edit. `Question.section` FK (§1.3)
is a DERIVED materialization recomputed from range, giving O(1) "what section is this question"
at grade time. (Rejected: M2M membership — unnecessary for Phase 3, adds a join everywhere,
complicates choose-k ordering. Defer until a non-contiguous use case appears.)

**Validation (`Section.clean()` + serializer):**
- `policy == choose_k` ⇒ `choose_k` not null AND `1 <= choose_k <= (q_end - q_start + 1)`.
- `q_start <= q_end`; both within `[1, test.questions.count()]`.
- Ranges of one test's sections must be **non-overlapping** (validate across siblings).
- Coverage MAY be partial (questions outside any section grade under the test scheme) — do not
  force full coverage (Mode A questions inside a competitive test still work).

### 1.2 NEW `assessments.SectionMarkingScheme` (OneToOne→Section)

```python
class SectionMarkingScheme(models.Model):
    NEG_FLAT = "flat"; NEG_FRACTIONAL = "fractional"
    NEG_KIND_CHOICES = [(NEG_FLAT, "Flat"), (NEG_FRACTIONAL, "Fractional")]

    section                  = models.OneToOneField(Section, on_delete=models.CASCADE,
                                                     related_name="marking_scheme")
    marks_per_correct        = models.DecimalField(max_digits=6, decimal_places=2, default=1)
    negative_marks_per_wrong = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    negative_kind            = models.CharField(max_length=12, choices=NEG_KIND_CHOICES,
                                                default=NEG_FLAT)
    partial_marking          = models.BooleanField(default=False)
    multiple_correct_allowed = models.BooleanField(default=False)
    qualify_pct              = models.DecimalField(max_digits=5, decimal_places=2,
                                                   null=True, blank=True)
```

**EXACT semantics of `negative_kind` (the spec's headline marking knob):**
- `flat`: WRONG penalty = `negative_marks_per_wrong` (subtract the stored Decimal directly,
  e.g. NEET store `1.00` → −1).
- `fractional`: WRONG penalty = `marks_per_correct * negative_marks_per_wrong`, i.e.
  `negative_marks_per_wrong` is interpreted as a FRACTION of `marks_per_correct`
  (UPSC −1/3 of 2 marks → store `marks_per_correct=2.00`, `negative_marks_per_wrong=0.3333…`;
  penalty `= 2 * (1/3) = 0.6667`). Compute the ratio in code with `Decimal("1")/Decimal("3")`
  where the fraction is exact — store `0.3333` only as a model value; grade.py should treat a
  fractional scheme as `penalty = marks_per_correct * negative_marks_per_wrong` using full
  `Decimal` precision and quantize ONCE at the end (§2.6). (Single field + `negative_kind` is
  leaner than a separate `negative_fraction` column and matches spec §2.)

`qualify_pct` (e.g. `33.00`) = CSAT qualifying-only: the section subtotal must reach
`qualify_pct/100 * section_max` to set `qualified=True`, but the section's marks **do NOT count
toward the aggregate** (qualifying gate only). `null` ⇒ section counts normally toward the
total. (`scheme_kind` MCQ/MSQ/numeric is a Mode-D1/Phase-5 concern — DO NOT add it now.)

### 1.3 CHANGED `assessments.Question` (+1 field)

```python
section = models.ForeignKey(Section, null=True, blank=True,
                            on_delete=models.SET_NULL, related_name="questions")
```

Nullable ⇒ standard tests + all existing rows unaffected. DERIVED from range: a
`Section.save()` / range-edit recomputes `Question.section` for questions whose
`order_index` (0-based) maps to 1-based ordinal in `[q_start, q_end]` via a single bulk
`UPDATE` (helper `Section.sync_question_membership()`). Range stays authoritative; FK is the
fast lookup at grade time and the stamping source for `QuestionResponse.section`.
**Do NOT add `kind`/`marks`/`negative_marks`/`numeric_answer` — those are Phase 5.**

### 1.4 CHANGED `results.QuestionResponse` (+1 field)

```python
section = models.ForeignKey("assessments.Section", null=True, blank=True,
                            on_delete=models.SET_NULL, related_name="question_responses")
# Meta.indexes += Index(fields=["student_result", "section"], name="qresponse_result_section_idx")
```

Denormalized section tag stamped at grade time (resolved from `question_order[q_pos] →
Question.section`). `null` for standard tests. Lets sectional analytics aggregate
`QuestionResponse` rows directly. Prefer STAMPING over deriving via `question.section`
because `question` may be null (SET_NULL) and `q_pos→section` needs the per-sheet
`question_order` anyway. **Existing keys/order of `QuestionResponse.create(...)` in
`_maybe_grade:341-348` stay; `section_id=...` is appended.**

### 1.5 CHANGED `assessments.Test` (+1 field, +1 choice)

```python
MODE_COMPETITIVE = "competitive"
MODE_CHOICES = [ ... existing ..., (MODE_COMPETITIVE, "Competitive (Sections)") ]
default_options = models.PositiveSmallIntegerField(default=4)   # 4 vs 5, per test
```

Real column (not buried in `template_spec`) for queryability + wizard binding. `default=4` ⇒
existing rows valid, standard tests unaffected.

### 1.6 OPTIONAL CHANGED `results.StudentResult` (+2 fields, recommended)

```python
section_breakdown = models.JSONField(default=dict, blank=True)
# {str(section_id): {"subtotal": float, "correct": int, "wrong": int, "blank": int,
#                    "q_count": int, "max_subtotal": float, "counts": bool,
#                    "qualify_pct": float|None, "qualified": bool}}
qualified_all     = models.BooleanField(default=True)
# AND over qualified flags of all sections that HAVE a qualify_pct; True (vacuous) for standard.
```

Clean persisted read path so analytics doesn't re-run marking. `default=dict` / `default=True`
⇒ standard tests unaffected. (If skipped, analytics re-derives from `QuestionResponse.section`
joined to the scheme — slower but possible; recommend including these.)

### 1.7 Migrations

1. **`backend/assessments/migrations/0004_section_modec.py`** (depends `0003_mode_and_template_spec`):
   `CreateModel Section`; `CreateModel SectionMarkingScheme`; `AddField Question.section`;
   `AddField Test.default_options (default=4)`; `AlterField Test.mode` to add the
   `competitive` choice (choices unenforced at DB → no-op SQL; existing rows keep `standard`).
2. **`backend/results/migrations/0005_questionresponse_section.py`** (depends
   `0004_publicresultshare`): `AddField QuestionResponse.section` + `AddIndex
   qresponse_result_section_idx`; (recommended) `AddField StudentResult.section_breakdown
   (default=dict)` + `AddField StudentResult.qualified_all (default=True)`.
3. **`backend/analytics/migrations/0002_...`** — ONLY needed if you add an optional
   `StudentProfile.section_breakdown JSONField(default=dict)` (§4.3). Per-section TEST stats go
   into the existing `TestProfile.profile` JSONField → **no analytics migration required** for
   the test-level profile.

**No data migration.** All defaults make existing rows valid immediately; no competitive
drafts exist in standard data. No `RunPython` backfill.

### 1.8 How a STANDARD test stays unchanged (the guarantee)

A standard test has: zero `Section` rows, zero `SectionMarkingScheme`, every
`Question.section IS NULL`, every `QuestionResponse.section IS NULL`,
`StudentResult.section_breakdown == {}`, `qualified_all == True`. It resolves the single
`Test.marking_scheme` OneToOne exactly as today. The grade loop reduces to today's branches
bit-for-bit (§2.7).

### 1.9 Scope isolation

`Section`/`SectionMarkingScheme` scope through `Test` (no user/org FK); all querysets filter
`section__test__user=request.user` XOR org, identical to `Question`/`MarkingScheme`.
`QuestionResponse.section` scopes through `student_result.test`. No new owner-scoped root tables.

---

## 2. The GRADING ALGORITHM (exact semantics, step by step)

Edit `backend/omr/scan/grade.py`. Keep the existing branch structure; insert four seams. All
section logic is **gated on section presence** so the standard path is untouched.

### 2.0 Inputs (unchanged signature)

`grade_sheet(omr_sheet, aggregated_reads)`. `answer_key = omr_sheet.answer_key`
(`{str(q_pos):[correct printed labels]}`); `aggregated_reads = {int(q_pos): [marked printed
labels]}`, absent = blank. Add ONE precomputed bridge at the top:

```python
question_order = omr_sheet.question_order or []   # list[Question.id], printed order
```

### 2.1 SCHEME-RESOLVER seam (replaces the single lookup at grade.py:46-57)

Build a per-q_pos scheme map BEFORE the loop. Keep the bare `try/except` ONLY for the
test-level fallback (do NOT put section resolution inside it — a bug there must not be masked
as "legacy default", per backward-compat risk).

```python
def _resolve_default_scheme(omr_sheet):
    # existing behavior: test.marking_scheme or 1/0/False/False
    try:
        ms = omr_sheet.test.marking_scheme
        return _scheme_tuple(ms.marks_per_correct, ms.negative_marks_per_wrong,
                             "flat", ms.partial_marking, ms.multiple_correct_allowed, None)
    except Exception:
        return _scheme_tuple(Decimal("1"), Decimal("0"), "flat", False, False, None)

# Per q_pos: resolve section + its scheme (OUTSIDE the except above)
def _scheme_for_qpos(q_pos, question_order, default_scheme, section_cache):
    if not question_order or q_pos >= len(question_order):
        return None, default_scheme
    q_id = question_order[q_pos]
    section = section_cache.get(q_id)          # Question.section (materialized FK), prefetched
    if section is None:
        return None, default_scheme            # Mode A question / uncovered → test scheme
    sms = getattr(section, "marking_scheme", None)
    if sms is None:
        return section, default_scheme         # section without override → test scheme
    return section, _scheme_tuple(sms.marks_per_correct, sms.negative_marks_per_wrong,
                                  sms.negative_kind, sms.partial_marking,
                                  sms.multiple_correct_allowed, sms.qualify_pct)
```

`section_cache` = one query: resolve all `Question.section` for `question_order` ids with
`select_related("section__marking_scheme")`. When there are **no sections at all**,
`section_cache` is empty/all-None and every q_pos uses `default_scheme` ⇒ identical to today.
A scheme tuple carries `(marks_per_correct, negative_marks_per_wrong, negative_kind,
partial, multiple, qualify_pct)`, all `Decimal(str(x))` numerics.

### 2.2 CHOOSE-K PRE-PASS seam (new, before the loop ~grade.py:66)

For each section with `policy == choose_k`, decide which q_pos are GRADED vs IGNORED.

- **"attempted" = any bubble marked** (`marked` non-empty in `aggregated_reads`). Blank = not
  attempted; blanks do NOT consume a slot.
- **Source order = PRINTED q_pos ascending** (the order bubbles appear on the sheet). This is
  the deliberate choice over underlying `question_order` order: it matches "first K the
  candidate filled top-to-bottom", is unambiguous, and the section's q_pos set is already a
  contiguous-ish slice. Document this in the docstring (spec §4.5 / §5 "first K attempted by
  q_pos order").
- Walk the section's member q_pos in ascending order; the FIRST `K` that are ATTEMPTED are
  ACTIVE; every later attempted q_pos in the section is `IGNORED`. Un-attempted (blank)
  questions are neither active nor ignored — they just don't fill a slot. If fewer than K are
  attempted, all attempted ones are active (no error).
- **Tie-break:** strictly ascending q_pos; no other tie possible (q_pos is unique).
- Produce `ignored_qpos: set[int]`. IGNORED q_pos score **0**, **no negative**, and do **NOT**
  enter `correct_count` / `wrong_count` / `blank_count` / `max_score` (backward-compat risk:
  counts must not be corrupted). They get a `per_question` entry with new status
  `"ignored"` (status field added; see §2.5) so the UI can show "not counted".

```python
def _choose_k_ignored(sections, members_by_section, aggregated_reads):
    ignored = set()
    for sec in sections:
        if sec.policy != Section.POLICY_CHOOSE_K or not sec.choose_k:
            continue
        attempted = [qp for qp in sorted(members_by_section[sec.id])
                     if aggregated_reads.get(qp)]      # non-empty marks
        for qp in attempted[sec.choose_k:]:
            ignored.add(qp)
    return ignored
```

### 2.3 SECTION-AWARE LOOP seam (grade.py:68-109, keep branches)

Loop over `answer_key.items()` in printed-q_pos order (unchanged). For each q_pos:

1. `if q_pos in ignored_qpos:` → status `ignored`, `question_score = Decimal("0")`,
   do NOT touch correct/wrong/blank, do NOT add to max (handled in §2.4), append per_question
   entry tagged `section` + `status="ignored"`, `continue`.
2. Resolve `(section, scheme)` via §2.1.
3. Apply the EXISTING four branches, but with the RESOLVED scheme's numbers:
   - **BLANK** (`not marked`): `blank_count++`, `question_score = 0`. (unchanged)
   - **EXACT** (`marked == correct`): `is_correct=True`, `correct_count++`,
     `question_score = marks_per_correct`. (unchanged)
   - **PARTIAL** (`partial and multiple and correct`): `raw = (|inter| − |over|)/|correct| *
     marks_per_correct`, `question_score = max(0, raw)`; if `>0` → `is_correct`,`correct_count++`
     else `wrong_count++`. (unchanged shape; per-q partial floor stays.)
   - **WRONG** (else): `wrong_count++`, `question_score = −penalty` where
     **`penalty = negative_marks_per_wrong` if `negative_kind=="flat"` else
     `marks_per_correct * negative_marks_per_wrong`** (the fractional rule, §1.2).
4. `score += question_score`.
5. Accumulate per-section buckets: `subtotals[section.key] += question_score`,
   `sec_correct/sec_wrong/sec_blank/sec_attempted` counters,
   `sec_q_count` (graded items in section, i.e. active members),
   `sec_max += marks_per_correct` (for max_subtotal — only ACTIVE members, see §2.4).
6. Append per_question entry: **keep the existing keys
   `{q_pos, marked, is_correct, flagged}` in the same names/values** (consumed at
   `_maybe_grade:321-325`) and ADD optional keys `section` (key str | None),
   `score` (Decimal), `status` ("correct"|"wrong"|"blank"|"partial"|"ignored").

### 2.4 max_score (the per-q-weight fix)

Today `max_score = len(answer_key) * marks_per_correct` (uniform). With per-section marks this
is wrong. Change to a **SUM over graded q_pos**, gated:

- **No sections present:** keep the cheap formula `len(answer_key) * marks_per_correct`
  (bit-for-bit identical to today).
- **Sections present:** `max_score = Σ over q_pos NOT in ignored_qpos of that q_pos's
  scheme.marks_per_correct`. IGNORED q_pos (choose-k surplus) and qualifying-only-section
  questions are handled per §2.5: ignored never enter max; qualifying-section questions DO
  contribute to `max_subtotal` of their section but NOT to the aggregate `max_score`.

Per-section `max_subtotal = Σ marks_per_correct over that section's ACTIVE members` (choose-k
sections cap at `K * marks_per_correct`).

### 2.5 SUBTOTAL / CUTOFF POST-PASS seam (after the floor, grade.py:112)

After the per-q loop:

1. **Aggregate floor:** `score = max(Decimal("0"), score)` — KEEP exactly as today (whole-test
   floor). This is the StudentResult.score.
2. For each section, compute `subtotal` (already accumulated). **Section floor policy
   (new knob, default OFF):** by default do NOT floor section subtotals (they may be negative,
   shown as-is); the aggregate floor is the only floor that affects `score`. (Document:
   summing displayed subtotals may differ from floored total when the raw total is negative —
   precedence: `StudentResult.score` = floored aggregate is authoritative; subtotals are raw.)
3. **Qualifying cutoff:** for sections with `qualify_pct` not null:
   `threshold = qualify_pct/100 * max_subtotal`; `qualified = subtotal >= threshold`.
   A qualifying-only section's subtotal is EXCLUDED from the aggregate `score` and from
   aggregate `max_score` (it is a gate, not a contributor) — set `counts=False`.
   **Do NOT silently zero the total** for a failed qualifying section. Instead expose:
   per-section `qualified` bool + overall `qualified_all = AND of qualified over all sections
   that have a qualify_pct` (vacuously True if none). Downstream (Results/report card) shows
   "Qualified / Not Qualified" without mutating the numeric score.
4. **Counting vs qualifying interplay:** a section WITHOUT `qualify_pct` → `counts=True`, its
   subtotal IS part of the aggregate. A section WITH `qualify_pct` → `counts=False`, gate only.

### 2.6 Quantization (decide once)

Today there is no `quantize`; fractional schemes (1/3) would round at `DecimalField(2)` on
save, so Python full-precision subtotals re-summed from rounded DB values can disagree
(backward-compat risk). **Decision:** compute the whole algorithm in full `Decimal` precision,
then **quantize ONCE at the boundary** — `score`, `max_score`, and each section
`subtotal`/`max_subtotal` to 2 dp (`Decimal.quantize(Decimal("0.01"),
ROUND_HALF_UP)`) right before returning. This keeps displayed subtotals consistent with the
total (all derived from the same quantized values) and matches the DB precision. Standard
tests (integer marks) are unaffected by quantize.

### 2.7 RETURN-CONTRACT seam (grade.py:114-121, additive)

```python
return {
    "score": score,                # quantized, floored
    "max_score": max_score,        # quantized SUM (or legacy product when no sections)
    "correct_count": correct_count,
    "wrong_count": wrong_count,
    "blank_count": blank_count,
    "per_question": per_question,  # each: existing keys + optional section/score/status
    # NEW optional keys (absent-safe for existing consumers):
    "sections": sections_out,      # [] when no sections
    "qualified_all": qualified_all,# True when no qualifying sections
}
```

`sections_out[i]` = `{"section_id", "key", "label", "order_index", "policy", "choose_k",
"subtotal", "max_subtotal", "q_count", "correct", "wrong", "blank", "counts",
"qualify_pct", "qualify_threshold", "qualified"}`. Existing consumers
(`_maybe_grade`, tests) ignore unknown keys ⇒ no break.

### 2.8 Persistence wiring (`pipeline._maybe_grade`)

- `StudentResult.update_or_create` defaults (`:300-312`) gain `"section_breakdown": {...}`
  (built from `grading["sections"]`) and `"qualified_all": grading["qualified_all"]`.
  Additive; standard path passes `{}` / `True`.
- `QuestionResponse.create` (`:341-348`) gains `section_id=` resolved from
  `question_order[q_pos] → Question.section_id` (one prefetched map; reuse the
  `section_cache`). Standard path → `None`. **Do not rename/reorder the existing kwargs;
  keep `flagged` set from job reads at `:328-333`.**
- `max_score` now a Decimal sum — `StudentResult.max_score` is `DecimalField(7,2)`, fine.

### 2.9 Floor-rule summary (precedence, to avoid 3-floor disagreement)

1. Per-question partial floor: `max(0, raw)` (unchanged, inside loop).
2. Aggregate floor: `score = max(0, score)` (unchanged) → authoritative `StudentResult.score`.
3. Section subtotals: NOT floored by default (raw, may be negative). If a future per-section
   floor knob is enabled it floors only the displayed subtotal, never `score`.
   Documented precedence: **aggregate floored total is the source of truth**; subtotals are
   informational and may sum to a different number when the raw total went negative.

---

## 3. Generator / geometry (headers without moving bubbles; 4-vs-5 options)

**Hard constraint:** SECTIONS ARE METADATA, NOT GEOMETRY. The scanner reads geometry purely
from `descriptor["answer_bubbles"][i]["options"][j] = {cx,cy,r}` (`read.py`), and each
`OmrSheet` stores its OWN frozen `template_descriptor`. Therefore `(cx,cy,r)` of existing
sheets must read identically forever. Generator and scanner consume ONE descriptor → compute
any header gap in `build_template` so both stay in lockstep.

### 3.1 `build_template` (geometry.py) — additive `sections` block

1. New optional param/spec field `sections` = list of authored section dicts
   `{key, label, order_index, q_pos_range:[lo,hi], policy:{type, k}}` where `q_pos_range`
   references EXISTING q_pos (printed positions for this sheet, derived from the per-sheet
   shuffle at generation time). Building this list does NOT relayout anything.
2. Tag each bubble: `answer_bubbles[i]["section"] = <section key>` (or omit when uncovered).
   Adding a dict key does NOT change `cx/cy`.
3. **Header vertical space — scanner-neutral approach (chosen):** when a new section starts at a
   row, advance the running `cy` by an extra `SECTION_HEADER_H` (e.g. 16 px) BEFORE that
   section's first row, and record `sections[i]["header_y"]` = the y of that reserved gap. Both
   bubble `cy` and `header_y` are computed in the SAME pass in `build_template`, so the gap is
   baked into the descriptor the scanner uses. The 22 px min `row_pitch` floor (`2*R+4`) is
   untouched — the gap is added BETWEEN rows, never by shrinking pitch. Re-validate the
   existing fit asserts with the added gap (page-count may rise for very dense section-heavy
   sheets — `page_count = ceil` recomputed from the gapped layout).
   **Legacy/standard sheets pass no `sections` → zero gap → identical layout & bytes.**
4. Emit top-level `descriptor["sections"]` (with `key,label,q_pos_range,policy,header_y,page`)
   and per-bubble `section`. Absence = legacy (read via `descriptor.get("sections")`).

### 3.2 Generator — NEW gated `_draw_section_headers`

`_draw_section_headers(c, descriptor, page_no, page_h_px)` gated on
`descriptor.get("sections")`, called per page inside the page loop, INDEPENDENT of
`_draw_answer_bubbles` (which is untouched). For each section whose questions fall on this
page, draw a band at `section["header_y"]` like `"Section A — Physics (Q1–35, all)"` /
`"Section B (attempt any 10 of 15)"`. **It only draws TEXT in the reserved whitespace gap; it
never alters the circle passes.** Legacy sheets (no `sections`) skip this pass entirely → zero
change to existing output (existing generator golden tests pass).

### 3.3 Scanner — NO change

`read_answers` walks `answer_bubbles[].options` by `(cx,cy,r)`; it ignores any descriptor key
it doesn't read (`sections`, per-bubble `section`). `simulate.py` iterates options only.
`decode_qr` is untouched (QR versioning is Phase 1/4). Section grading/analytics consume
`answer_bubbles[i].section` / `QuestionResponse.section` downstream, not the CV reader. Full
backward-compat by construction.

### 3.4 4-vs-5 options end to end

Engine already supports 5 (and 6) — clamp is `[2,6]` in both `geometry.py:77` and
`views.py:201`, NOT `[2,4]`; horizontal fit for 5 verified (col1 5-opt right edge 541 px ≪
787 page-margin). What changes to make 4-vs-5 a first-class per-test CHOICE:

1. **DATA:** `Test.default_options` (§1.5).
2. **GENERATE FLOW (`views.py:197-201`):** honor it —
   `num_options = max(2, min(6, max(test.default_options, max_options)))` so a 5-option test
   always lays out 5 columns even if some questions define only 4 real options. Keep the
   `[2,6]` clamp.
3. **WIZARD:** 4-vs-5 toggle writing `Test.default_options` (§5).
4. **KEY/SHUFFLE:** `shuffle.build_sheet_plan` already covers all 5 labels (label-driven).
   Add a wizard/serializer VALIDATION WARNING when a 5-option test has any question with <5
   options (a blank distractor column) — warn, don't block.
5. **TESTS:** `tests_omr.py` already parametrizes `num_options` and asserts each bubble has
   `num_options` options; add an end-to-end `default_options` test (§6 task 3B).

---

## 4. Sectional analytics (added to `TestProfile.profile`)

No schema change to `TestProfile` (uses existing `profile` JSONField). Standard tests omit the
`sections` key (or emit `[]`) → existing `tests_analytics.py` golden fixtures pass unchanged.

### 4.1 `build_results_data(test)` extension (`psychometrics.py:555`)

Each per-student dict gains:
```python
"section_scores": {
    section_id: {"subtotal": float, "correct": int, "q_count": int, "qualified": bool}
}
```
Cleanest source = read `StudentResult.section_breakdown` (§1.6) directly (no marking
recompute). Fallback = aggregate `QuestionResponse.section` joined to scheme. When the test has
no sections, omit the key (or `{}`) ⇒ output byte-identical to today.

### 4.2 `compute_test_profile(results_data, sections=None)` extension (`psychometrics.py:391`)

Add an OPTIONAL `sections` arg (list of `{section_id, key, label, order_index, policy,
choose_k, qualify_pct, max_subtotal}` plus per-student `section_scores`). When `None`/absent →
behave exactly as today (no `sections` key in the returned dict). When present, add
`profile["sections"]` via a NEW pure function `compute_section_stats(...)`:

```python
profile["sections"] = [
  {
    "section_id", "key", "label", "order_index", "policy", "choose_k",
    "q_count", "max_subtotal",
    "qualify_pct", "qualify_threshold",   # threshold = qualify_pct/100 * max_subtotal
    "counts": bool,                       # False when qualify_pct set (qualifying-only)
    "mean_subtotal", "median_subtotal", "stddev_subtotal",
    "min_subtotal", "max_subtotal_obs",
    "mean_accuracy",                      # mean of (correct / q_count)
    "qualified_count", "qualified_pct",   # cohort cutoff pass-rate
    "toppers": [{"student_id","student_result_id","subtotal","section_rank"} ...top N],
    "subtotals": [{"student_id","student_result_id","subtotal","accuracy","qualified"} ...]
  }, ...
]
```

`compute_section_stats` is a pure function (mean/median/stddev over subtotals, toppers,
qualified_count) consistent with the existing pure-function style and unit-testable with
fixtures. Respect `MIN_COHORT_FOR_PSYCHOMETRICS=10`: below it, return basic per-section stats
(mean/median/min/max/qualified_count) but mark cohort-sensitive aggregates
`{"status":"insufficient_sample","n":n}` — same convention as the rest of the module.

### 4.3 Per-student (optional)

Either fold per-student section breakdown into `profile["sections"][].subtotals`, OR add
`StudentProfile.section_breakdown JSONField(default=dict)` (`{section_key:{subtotal, accuracy,
rank, qualified}}`) for the report-card radar/heatmap (spec §5.2/§5.3). Recommended but
optional for Phase 3; if added → analytics migration `0002` (§1.7).

### 4.4 Task / endpoint

`analytics.tasks.recompute_test_profile` passes `sections` + `section_scores` into
`compute_test_profile` when the test has sections; otherwise calls it unchanged. Analytics
endpoint returns `profile["sections"]` as-is (additive); old endpoints/columns unchanged.

---

## 5. Frontend

### 5.1 `TestWizard.jsx` — SECTION BUILDER + options toggle

- **Mode select:** add "Competitive (Sections)" → sets `Test.mode = "competitive"`.
- **Options toggle:** custom segmented control 4 / 5 (NO native `<select>`) → `default_options`.
- **Section builder** (shown for competitive mode): a custom list editor where each row =
  `{key, label, q_start, q_end, policy (all|choose_k), choose_k}` + a collapsible per-section
  marking panel `{marks_per_correct, negative_marks_per_wrong, negative_kind (flat|fractional),
  partial_marking, multiple_correct_allowed, qualify_pct}`. Inline validation mirrors §1.1/§1.2:
  non-overlapping ranges, `choose_k` within range, ranges within question count. Use existing
  custom inputs/toggles/modal (no `alert/confirm/prompt`). A live "coverage" strip shows which
  Q ordinals belong to which section and which are uncovered (grade under test scheme).
- POSTs to new section CRUD endpoints (`/api/v1/tests/<id>/sections/` + nested
  `marking_scheme`), owner-scoped through the test.

### 5.2 `Results.jsx` + report card — surface subtotals/qualification

- Results table: expandable per-student row showing `section_breakdown` (subtotal /
  max_subtotal, correct/wrong/blank, and a "Qualified"/"Not Qualified" chip per qualifying
  section) plus an overall `qualified_all` badge. Aggregate `score` stays the headline number
  (qualifying-only sections shown as gates, not added).
- Branded PDF report card (`analytics/report_card.py`): add a "Sectional breakdown" block
  (per-section subtotal, accuracy, section rank, qualification) when the test has sections;
  omit for standard tests (no layout change to existing cards).

### 5.3 `Analytics.jsx` — sectional profile

When `profile.sections` present: per-section cards with subtotal distribution (reuse histogram
component), per-section toppers (top N), and cutoff pass-rate (`qualified_pct`). Hidden for
standard tests (no `sections` key) → existing Analytics view unchanged.

---

## 6. Task breakdown (each independently testable)

### Task 3A — Backend models + grading
**Goal:** Sections, per-section marking, choose-k, subtotals, cutoffs, persistence; standard
path bit-for-bit unchanged.
**Build:** §1 models + migrations (`assessments 0004`, `results 0005`); §2 `grade.py`
resolver + choose-k pre-pass + section loop + subtotal/cutoff post-pass + additive return +
quantize; §2.8 `_maybe_grade` persistence (stamp `QuestionResponse.section`,
`StudentResult.section_breakdown`/`qualified_all`); `Section.sync_question_membership`; section
CRUD serializers/views (owner-scoped).
**Tests (golden grading cases — extend, never loosen existing):**
1. **Backward-compat no-sections:** a test with no sections grades to the EXACT same
   `score/max_score/correct/wrong/blank/per_question` as today (assert against current
   fixtures; existing `tests_omr`/`tests_scan` unchanged).
2. **Flat negative (NEET-style):** section +4/−1 flat → wrong subtracts exactly 1; exact adds 4.
3. **Fractional negative (UPSC −1/3):** section `marks_per_correct=2`,
   `negative_kind=fractional`, `negative_marks_per_wrong=1/3` → wrong penalty = 0.6667 (assert
   quantized 0.67); verify full-precision sum then single quantize.
4. **Choose-k grades only first K attempted:** section of M=15, `choose_k=10`; mark 12 → first
   10 by ascending q_pos graded (correct/wrong as keyed), the 2 surplus = `status=ignored`,
   score 0, no negative, NOT in correct/wrong/blank or max_score; blanks don't consume slots
   (mark non-contiguously to prove ordering).
5. **Sectional cutoff qualification:** section `qualify_pct=33`; subtotal at 32% →
   `qualified=False`; at 34% → `qualified=True`; qualifying-only section EXCLUDED from
   aggregate `score`/`max_score`; `qualified_all` = AND over qualifying sections; failing a
   gate does NOT zero the total.
6. **Subtotal sums + floor precedence:** Σ counting-section subtotals (+ uncovered) == floored
   aggregate `score` when total ≥ 0; when raw total < 0, `score` floors to 0 while raw
   subtotals stay negative (documented).
7. **Resolver fallback:** section without `SectionMarkingScheme` → uses test scheme; uncovered
   question → uses test scheme; bug in resolver must NOT be swallowed by the test-level
   `except`.
8. **Persistence:** `QuestionResponse.section` stamped correctly via shuffled
   `question_order`; `StudentResult.section_breakdown`/`qualified_all` persisted; per_question
   keys `{q_pos,marked,is_correct,flagged}` still present/ordered.

### Task 3B — Generator + geometry
**Goal:** Section headers without moving bubbles; 4-vs-5 surfaced.
**Build:** §3.1 `build_template` `sections` block + per-bubble `section` + computed
`header_y`/gap; §3.2 gated `_draw_section_headers`; §3.4 `views.py` honor `default_options`;
5-option validation warning.
**Tests:**
1. **Bubble-coord invariance:** for fixed `(num_questions, num_options)`, `answer_bubbles`
   `(cx,cy,r)` are IDENTICAL with vs without a `sections` block when headers add zero gap;
   when a gap is added, generator-drawn header_y equals descriptor `header_y` (lockstep) and
   scanner reads the same bubbles (`simulate → read` round-trip unchanged).
2. **Legacy descriptor:** no `sections` key → `_draw_section_headers` no-ops; existing
   generator golden output byte-identical.
3. **5 options end-to-end:** `Test.default_options=5` → 5 bubble columns laid out even when a
   question has 4 options; horizontal fit asserts hold; `simulate` can mark "E"; `read`
   classifies E.
4. **Scanner ignores section keys:** `read_answers` output identical with/without per-bubble
   `section` tags.

### Task 3C — Analytics + frontend
**Goal:** Sectional stats in `TestProfile`; wizard builder; Results/report-card/Analytics
surfacing.
**Build:** §4 `build_results_data` `section_scores` + `compute_test_profile(sections=...)` +
pure `compute_section_stats` + task wiring; §5 wizard section builder + options toggle, Results
section breakdown + qualification chips, report-card sectional block, Analytics sectional cards.
**Tests:**
1. **Golden section stats:** known fixture cohort → expected `mean/median/stddev_subtotal`,
   `toppers`, `qualified_count`/`qualified_pct` (pure-function unit tests).
2. **Backward-compat analytics:** test with no sections → `compute_test_profile` output has NO
   `sections` key and is byte-identical to today (existing `tests_analytics.py` fixtures pass).
3. **Insufficient sample:** cohort < 10 → per-section cohort aggregates marked
   `{"status":"insufficient_sample"}` per existing convention; basic stats still returned.
4. **Frontend:** section builder validates overlap/choose_k inline (no native dialogs);
   Results shows subtotal + qualification; standard test renders unchanged.

### Task 3D — E2E (cross-browser, Playwright)
**Goal:** Spec §6 Phase-3 acceptance.
**Flow:** create a 2-section competitive test (Section A = "all", Section B = choose-k) with 5
options → define per-section marking (one flat, one with `qualify_pct`) → generate (printed
sheet shows section header bands, bubbles unmoved, 5 columns) → simulate/scan a cohort → open
the test profile: per-section subtotals, toppers, and cutoff qualification appear; a student's
Results row shows section breakdown + Qualified/Not-Qualified; report card PDF includes the
sectional block.
**Guard:** also run an existing STANDARD-mode E2E to confirm zero regression.

---

## 7. Backward-compatibility checklist (must all hold)

1. No sections ⇒ `max_score` keeps the legacy `len(answer_key)*marks_per_correct` product
   (per-q sum only when sections exist).
2. Section resolution lives OUTSIDE the test-level `try/except` so resolver bugs aren't masked
   as "legacy 1/0 default".
3. Choose-k IGNORED questions never enter `correct/wrong/blank`/`max_score`; "source order" is
   fixed as ascending printed q_pos (documented).
4. `per_question` keys `{q_pos, marked, is_correct, flagged}` keep names/order (unpacked at
   `_maybe_grade:321-325`); `flagged` still set in pipeline; new keys are additive/optional.
5. Three floors have defined precedence: floored aggregate `score` is authoritative; subtotals
   raw (informational); partial floor unchanged.
6. Quantize ONCE at return boundary (2 dp) so re-summed subtotals match the total and the DB
   `DecimalField(2)` precision.
7. New return keys (`sections`, `qualified_all`) + per_question `section/score/status` are
   additive/optional — existing consumers and tests ignore them.
8. Descriptor: sections only appear on newly generated competitive sheets; all reads gated on
   `descriptor.get("sections")`; old sheets' `(cx,cy,r)` read identically forever.
9. Analytics `sections` arg optional; absent ⇒ output byte-identical to today.
10. All migrations additive/reversible; no data migration; standard rows valid by default.
