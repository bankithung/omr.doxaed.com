# OMRFlow: ranked implementation plan

## 1. Verdict

### (a) Can a school teacher and a coaching institute complete the flow end to end?

**School teacher on a laptop with a clean scan: yes. School teacher with a phone, which is the stated primary input: no. Coaching institute: no.**

Exactly where it breaks:

| # | Break point | Who it stops |
|---|---|---|
| 1 | **Photographing a sheet on any surface darker than grey 220 fails alignment outright.** Global Otsu on the full frame (`backend/omr/scan/align.py:124`) makes the desk read as ink; the fiducials dissolve. Verified cliff: bg 220 works, bg 210 and below fails, 0 questions read, error is the raw token `alignment`. A desk, a table, a notebook or a coloured mat all fail. | Teacher. This is *the* phone flow. |
| 2 | **Light pencil reads as blank at confidence 1.0 with a green CLEAN badge.** `read.py` binarises before measuring, so `fill_ratio` is quantised to ~0.0 or ~1.0 and the FILL_LOW 0.20 / FILL_HIGH 0.45 review band is **unreachable for a uniformly shaded mark**. Verified cliff at ~grey 145. A student who answered all 10 correctly in HB pencil is handed 0/10 and the product calls it clean. | Both. This is the trust kill. |
| 3 | **Re-scanning a sheet UNIONs every scan ever taken of it** (`pipeline.py:_maybe_grade` filters on `omr_sheet` + status only, then extends marks). Verified in psql: 7 jobs across 6 batches for one sheet, `q0` holding both "D" and "A". A control sheet with 10 correct marks scored 1/10. **Retrying a bad photo makes the score worse, permanently.** There is no recovery path from break 1 or 2. | Both. |
| 4 | **Resolving a review item writes the teacher's answer onto the wrong question.** `backend/results/views.py:147` does `QuestionResponse.objects.filter(student_result=..., flagged=True).first()` — the ReviewItem's own `question` FK is **never populated** (`_create_review_item` never passes it). With flags on Q3 and Q7, resolving the Q7 card edits Q3. | Both. |
| 5 | **One exam printed across a class and its sections silently omits students.** Generate posts a single `roster` id; the class roster and each section roster are separate. Verified: class header says 17 students, Generate says "10 of 10 selected", 7 students get no sheet, no warning. Discovered in the exam hall. | Teacher (sections), institute (batches). |
| 6 | **No bulk student entry.** 4 modal interactions per student and the modal closes after every save. 300 students ≈ 1200 interactions. `add_count` is capped at 10 in the UI and `IntegrityError`s on a non-empty roster. | Institute. Hard stop at onboarding. |
| 7 | **Free plan is 1 seat and the app never says so.** Invite is fully enabled, the 403 arrives as a 5 second toast with no link, the dialog stays open and filled with no inline error. The one moment an institute would have paid you. | Institute. |
| 8 | **Nothing can be deleted or renamed.** Abandoning the wizard after step 1 persists a DRAFT exam forever. The live demo list already carries 13 exams, 10 DRAFT, **five identically titled and identically dated**. DRAFT rows still print. | Institute (weekly tests). |
| 9 | **Below `lg`, the mobile drawer is a hardcoded two item list.** Review is unreachable, and the entire org admin area (Roles, Usage, Billing, Settings, Audit) has zero entry point. The device you scan from is the device that cannot open the review queue. | Both. |

Everything else in the corpus is pain on top of a job that completes.

### (b) Is the QR + sheet + scanner design good enough to trust in a real classroom?

**The design is right. The implementation is not, and it fails in the one direction you cannot tolerate: silently, with a confident number attached.**

What is genuinely sound and should not be redesigned: per sheet stored `answer_key` and `template_descriptor` (so already printed sheets survive any layout change, and grading against a stale key is structurally impossible); QR carrying `sheet_code|page|total`; four corner fiducials; the review queue concept; scoping and ownership.

What must change before you can trust a score:

1. **Crop to the page before thresholding.** Nothing else in `align.py` matters until the histogram is paper versus ink instead of paper versus desk. This also buys perspective correction, which the code does not do *at all* today, so every handheld photo is currently read on a keystoned grid.
2. **Stop binarising before measuring.** Measure greyness against a local paper reference and a per page ink reference. Until this lands, the "faint marks go to review" promise the product sells does not exist: a mark is silently perfect or silently absent.
3. **Confidence is a tautology.** `(n_questions - n_flagged) / n_questions` is 1.0 whenever nothing was flagged, which is precisely the case where it should be low. It reports 100% on a page it read entirely wrong.
4. **Fiducials are not orientation unique and the candidate filter is too loose.** A sheet fed upside down grades near zero at 96% confidence. A stapled or torn corner lets an *answer bubble* qualify as a fiducial, producing a believable wrong score rather than a clean failure.
5. **The sheet tells the student nothing.** No "fill completely", no "black or blue ballpoint", no "do not fold or staple". The two failure modes above are exactly the ones instructions prevent, and the sheet has half an A4 of blank space to print them in.

> **Explicit caveat on the optical verdict.** No agent tested a real camera photo of a physically printed sheet. Every optical finding above comes from synthetic composites, re dimension re-rendered PDFs at 3x, and reading the code path. Blur, shadow gradients, phone HDR and tone mapping, printer toner variation, paper gloss and real keystone are **unmeasured**. The failures listed are real because they were reproduced through the running pipeline, but the *magnitude* of the fix needed is a code path judgement, not a field measurement. **Item 0 below exists because of this.**

---

## 2. Fix now

Ordered. Ship in this order; items 1 to 4 are the trust core and 0 gates all of them.

---

### 0. Build a real photo corpus and a scoring harness (do this first, it is 1 day)

**Why:** Every optical fix below is currently unfalsifiable. You cannot tell a real improvement from a synthetic one.

**What:** Print 20 real sheets from the product. Get them filled by hand: 5 in HB pencil, 5 in blue ballpoint, 5 in black gel, 5 deliberately abused (one folded corner, one stapled, one upside down, one photocopied, one with ticks instead of fills). Photograph each with a phone on: white paper, a wooden desk, a dark table, under a window with a shadow across the page, and at a 20 degree tilt. That is ~100 images with a known ground truth key.

Commit them under `backend/omr/fixtures/photos/` with a JSON ground truth, and add `backend/omr/tests_photos.py` asserting per image: alignment succeeded, and answers match ground truth. Report the pass rate as a single number. **Today's number is the baseline. Do not merge any scan change that does not move it.**

**User notices:** nothing yet. This is the only reason you will know items 1 to 4 worked.

---

### 1. Rewrite the alignment front end: crop the page, then threshold

**Files:** `/home/user/omr.doxaed.com/backend/omr/scan/align.py`

**What changes:**
- New first stage in `detect_fiducials`'s caller path, before any inverse threshold: Otsu **non-inverse** on the full frame (this is exactly the threshold 224 that breaks detection today, used as the signal instead of the bug) → morphological close → largest external contour → `cv2.approxPolyDP` at 2% arc length. If 4 points, order them TL/TR/BL/BR and `cv2.warpPerspective` to an upright page of aspect `descriptor["page_px"]`. If not 4 points, fall back to `cv2.minAreaRect`.
- Run `decode_qr` and `detect_fiducials` **on the cropped page**. After the crop the existing Otsu at `align.py:124` works unchanged.
- Only if the quad search fails entirely, fall back to `adaptiveThreshold(gray, 255, ADAPTIVE_THRESH_GAUSSIAN_C, THRESH_BINARY_INV, blockSize=odd(6*FID*img_scale), C=10)` for fiducial hunting, keeping the existing area/squareness/solidity filters to reject adaptive noise.

**Do not** make "print a border rectangle inside the margin" the primary fix. It is a print-template change that invalidates every sheet already printed.

**User notices:** photographing a sheet on a desk works. This is the difference between "phone camera product" and "flatbed scanner product".

---

### 2. Validate the fiducial quad, and detect 180 degree rotation

**Files:** `/home/user/omr.doxaed.com/backend/omr/scan/align.py`, `/home/user/omr.doxaed.com/backend/omr/scan/pipeline.py`

**What changes:**
- **Before warping**, after picking 4 candidates: the two horizontal spans must agree within ~5%, the two vertical spans likewise, and width:height must match the descriptor's 827:1169 within tolerance. Fail → `alignment` review item, never a warp.
- Tighten the candidate filter to `solidity >= 0.85` and area within `[0.6x, 1.8x]` of expected, so a hollow answer bubble cannot qualify as a fiducial.
- **After warping**, re-detect the QR on the canonical image and assert its bounding box lands inside the descriptor's `qr` rect. Lands in the opposite corner → rotate 180 and re-warp. Lands anywhere else → flag `alignment` instead of grading.

**User notices:** a sheet fed upside down is graded correctly instead of scoring near zero at 96% confidence. A stapled or torn corner produces "could not read this sheet" instead of a plausible wrong score.

---

### 3. Stop binarising before measuring; make confidence mean something

**Files:** `/home/user/omr.doxaed.com/backend/omr/scan/read.py`, `/home/user/omr.doxaed.com/backend/omr/scan/pipeline.py`

**What changes in `read.py`:**
- Remove `to_binary` from the measurement path. `bubble_fill_ratio` measures greyness against a **local** reference:
  - `paper` = median intensity of the annulus `r*1.7 .. r*2.4` around the bubble (outside the printed ring, inside the row gap)
  - `ink_ref` = 5th percentile intensity of the QR module block from the descriptor (a guaranteed black patch **on that same page**, so exposure and white balance cancel)
  - `darkness = clip((paper - mean(inner disc r*0.6)) / max(paper - ink_ref, 40), 0, 1)`
- Feed `darkness` into the existing `classify()`. Grey 150 pencil on grey 250 paper then scores ~0.3 and lands in the ambiguous band → review queue, instead of 0.0 → silent blank.
- Add the per row relative rule on top: mark the option with max darkness **only if** it clears an absolute floor **and** beats the runner up by >= 0.15. Top two within 0.15, or top between FILL_LOW and FILL_HIGH → flag `ambiguous`.

**What changes in `pipeline.py` (lines 261 to 267):**
- Replace `(n_questions - n_flagged) / n_questions` with the **minimum per question margin**: `min over q of |darkness_top - decision_threshold|`, scaled to [0,1]. A page of borderline pencil then reports low confidence even with zero flags.
- When `read_answers` returns zero marked options across **every** question on a page, append an `all_blank` flag, map it in `_flag_to_reason`, and raise a ReviewItem. A genuinely blank sheet is worth one click to confirm; a misread page is worth catching.
- On `flags == ['alignment']`: do not print the sheet's previous score, do not count it in "processed successfully", and emit an actionable sentence, e.g. "Could not find the four corner squares. Photograph the sheet on a plain white surface with all four corner squares inside the frame."

**Related, same wave (`backend/omr/generator.py`):** the option letter is currently printed **inside** each bubble, consuming most of the "empty bubble" ink budget and pushing the baseline toward FILL_LOW. Move the letter outside the circle (immediately left of it, or as a column header). This is not cosmetic; it restores the full 0 to 0.20 band as genuine headroom and materially reduces false `faint` flags once item 3 is measuring greyness.

**User notices:** a pencil sheet either grades correctly or lands in the review queue. It never comes back as a confident zero. The confidence number becomes something a teacher can act on.

---

### 4. One authoritative scan per (sheet, page); never union reads

**Files:** `/home/user/omr.doxaed.com/backend/omr/scan/pipeline.py` (`_maybe_grade`, ~line 302 to 340), `backend/omr/models.py` (new `ScanJob.STATUS_SUPERSEDED`), `backend/omr/views.py` (`OmrSheetRegradeView`)

**What changes:**
- When a new job completes for a `(omr_sheet, page_no)` that already has a done or needs_review job, mark the older job `superseded` and exclude it from both `_maybe_grade` and the regrade aggregation. Never `.extend()` marked labels across jobs.
- Surface the conflict rather than hiding it: "This sheet was scanned on 24 Jul and scored 7 of 10. The new scan scores 9 of 10. Keep new / keep old."

**User notices:** re-photographing a badly lit sheet fixes it instead of corrupting it. Without this, items 1 to 3 have no recovery path and every retry compounds the error.

---

### 5. A review resolution edits the question it was raised for

**Files:** `/home/user/omr.doxaed.com/backend/results/models.py`, `/home/user/omr.doxaed.com/backend/omr/scan/pipeline.py` (`_create_review_item`), `/home/user/omr.doxaed.com/backend/results/views.py` (~line 147), `backend/results/serializers.py`, `/home/user/omr.doxaed.com/frontend/src/routes/ReviewQueue.jsx`

**What changes:**
- Add `q_pos` (integer, nullable) to `ReviewItem` and populate it in `_create_review_item` — the pipeline already knows the flagged `q_pos` at the call site (`pipeline.py:292`). Populate the existing `question` FK at the same time by resolving through `omr_sheet.question_order`.
- Replace `filter(student_result=..., flagged=True).first()` with `QuestionResponse.objects.get(student_result=..., q_pos=review_item.q_pos)`, returning 400 on mismatch.
- Resolve **only** the items whose `q_pos` the teacher actually changed. Sheet level items (`roll_unreadable`, `roll_mismatch`, `missing_page`) stay open, and the response reports "1 flag fixed, 1 identity flag still open". Drive the result card state from the server response, not from a hard coded client assumption.
- `ReviewQueue.jsx` currently renders "Mark correct answer(s): A B C D E" + Resolve **unconditionally**. Branch on reason: for `test_mismatch`, `unknown_sheet`, `no_qr`, `alignment`, `missing_page` show an informational card with no option chips and a single real action (re-upload / reassign / discard).
- Backfill migration: existing ReviewItems get `q_pos = NULL` and their cards render as "reason unknown, re-scan this sheet" rather than an editable picker.

**User notices:** correcting Q7 changes Q7. Today it can change Q3 and the teacher will never know.

---

### 6. Print coverage: a print run's unit is a set of students, not a roster

**Files:** `/home/user/omr.doxaed.com/frontend/src/routes/GenerateSheets.jsx`, `/home/user/omr.doxaed.com/frontend/src/routes/class/ClassStudents.jsx`, `/home/user/omr.doxaed.com/backend/omr/views.py`

Two one line changes kill most real world incidence; then the structural repair.

1. `ClassStudents.jsx:45` — default the Add student dialog to the class, not `sections[0]`: `useState(String(classId))`. Filing a student under a section must be deliberate.
2. `GenerateSheets.jsx:86` `rosterLabel()` — stop labelling the class level roster "Grade 10". It is *students not in any section*, which `ClassStudents.jsx:151` already calls "Direct (no section)". Render "Grade 10 (no section)". Two screens currently use different words for the same set and the same words for different sets, which is what makes the omission invisible.
3. Structural: `loadTest()` already enumerates every roster in the class tree (`GenerateSheets.jsx:120-132`). Fetch students for all of them up front, render one list grouped by section with a per group select all, plus a top level "Select all 17 students in Grade 10" that is **on by default** when the exam's `class_group` is the parent class. Backend: make `roster` optional in `omr/views.py:106`, accept `student_ids` alone, derive each student's roster via the FK, and validate every derived roster with the existing `parent_in_scope` **and** that its `class_group` is the test's group or a descendant. Skipping that second check turns `student_ids` into a cross class print primitive.
4. Persistent, non dismissible coverage banner computed from the **class tree totals**, not from the selected roster: "17 students in Grade 10. 10 selected. 7 not covered." with a "Select all 17" action. Deriving it from the selected roster means it can never detect the gap it exists to catch.
5. Fix the picker while you are in it: `max-h-56` → `max-h-[60vh] overscroll-contain`, drop `sm:max-w-sm` from line 476 so the block uses full card width, render rows as `grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3`, add a debounced search on name and roll. **Select all must apply to the visible subset while preserving selections outside the filter** (`toggleAllStudents` at line 180 currently sets from the full array; naive filtering silently drops off screen students from the batch). Row `min-h-[36px]` → `min-h-[44px]`; replace the 43x16px "Select all / Clear all" text button with a `min-h-[40px]` outline Button.

**Also here, same print family (`backend/omr/geometry.py`):** size `roll_digits` from the widest roll number **string** in the roster, not the parsed integer. A student printed as "006" currently gets two digit columns and physically cannot bubble their roll. Make truncation loud: return 400 naming the roll and grid width rather than printing a wrong sheet.

**User notices:** the sheets you print match the class you think you printed for, and students can fill in their roll number.

---

### 7. Delete and rename exams; refuse to print an empty one

**Files:** `/home/user/omr.doxaed.com/frontend/src/api/assessments.js`, `/home/user/omr.doxaed.com/frontend/src/routes/TestList.jsx`, `/home/user/omr.doxaed.com/frontend/src/routes/exam/ExamOverview.jsx`, `/home/user/omr.doxaed.com/frontend/src/routes/GenerateSheets.jsx`

The backend already supports this: `TestViewSet` extends `ScopedModelViewSet` (a `ModelViewSet`), so `DELETE /api/v1/tests/:id/` is routed and scope gated. This is frontend only.

1. `assessments.js` — one missing line: `export const deleteTest = (id) => api.delete(\`/tests/${id}/\`).then((r) => r.data)`
2. `TestList.jsx` `TestActions` menuItems (lines 82 to 110) — add **Rename** (small Dialog + Input, calls the already exported `updateTest(id, {title})`) and **Delete exam** (destructive, using the custom Dialog pattern already in the same file at lines 240 to 255). Never `window.confirm`. Hard warn naming counts when the exam has sheets or results: "This exam has 10 generated sheets and 7 graded results." Both call back into `ExamsSection.fetchTests`.
3. Put the same two on `ExamOverview.jsx`. A row kebab in a table is not discoverable enough to be the only home.
4. Make rows distinguishable with no migration: `TestList.jsx:780-794` renders Created with `toLocaleDateString` month/day/year only. Add hour and minute, and add a Questions column (`question_count` is already on the serializer). That separates the five identical rows sitting in the demo data today.
5. Guard the empty draft where it leaks: disable Generate sheets when `question_count === 0` with the reason shown ("Add questions first"), on both `TestList.jsx:115-122` and `GenerateSheets.jsx`. A 0 question exam can currently print 10 blank sheets for a whole roster in one click.

**Do not** defer test creation to Finish (see Skip). **Do not** add a 24h draft sweep cron.

**User notices:** the exam list stops growing monotonically with undeletable garbage, and a typo'd title stops being permanent.

---

### 8. Bulk student entry

**Files:** `backend/rosters/views.py`, `backend/rosters/serializers.py`, `/home/user/omr.doxaed.com/frontend/src/App.jsx`, `/home/user/omr.doxaed.com/frontend/src/routes/AddStudents.jsx`, `/home/user/omr.doxaed.com/frontend/src/routes/RosterDetail.jsx`, `/home/user/omr.doxaed.com/frontend/src/routes/class/ClassStudents.jsx`, `/home/user/omr.doxaed.com/frontend/src/api/omr.js`

1. **Backend first, nothing works without it.** `POST /api/v1/rosters/{id}/bulk_add` taking `{students: [{roll_number, full_name}], on_duplicate: "skip"|"update"|"error"}`. One atomic transaction, enforce the `(roster, roll_number)` unique constraint plus in payload duplicates, return `{created, skipped, updated, errors: [{index, roll_number, message}]}` so the UI flags exact rows. Cap at a few thousand rows. Tests for duplicate rolls, blank rolls, and scope isolation (a roster the caller does not own must 404) per the project rule.
2. **Wire up the page that already exists.** `/home/user/omr.doxaed.com/frontend/src/routes/AddStudents.jsx` is a complete rapid entry page (form stays put, clears after each add, running "Added this session (N)" list) that **nothing imports** and no route registers. Register `/rosters/:id/add-students` and `/classes/:id/students/add`, and replace the `AddStudentDialog` / `AddBlankSheetsDialog` usages in `RosterDetail.jsx` with links to it.
3. **Import panel** above the single add form: textarea accepting pasted `Roll<tab>Name` or `Roll,Name` (tab separated is what an Excel column paste produces), plus a `.csv` drop zone. Parse client side into a preview table with a per row status column (new / duplicate in file / already in roster / missing roll), an `on_duplicate` choice, and one Import button posting to `bulk_add`, then re-render the preview with the server's per row errors. Header row detection and a column mapping row for real exported files.
4. **Cheap wins in the same change:** prefill Roll number with `(highest existing numeric roll + 1)` preserving zero padding width (009 → 010), refocus the name field after each save, fix `add_count` to start numbering after the current maximum instead of hardcoding 1..N (it currently `IntegrityError`s on any non-empty roster), and drop the `max="10"` UI cap at `RosterDetail.jsx:146`.

**User notices:** an institute onboards 300 students by pasting a spreadsheet column instead of 1200 modal interactions.

---

### 9. Students are editable

**Files:** `/home/user/omr.doxaed.com/frontend/src/api/omr.js`, `/home/user/omr.doxaed.com/frontend/src/routes/class/ClassStudents.jsx`

`rosters/views.py:94` is already a full `ModelViewSet`; PATCH and DELETE exist and are unused. `api/omr.js` exposes only `listStudents` and `addStudent`.

1. `api/omr.js`: `updateStudent = (id, d) => api.patch(...)`, `deleteStudent = (id) => api.delete(...)`.
2. Per row `<DropdownMenu>` kebab, `className="size-10 shrink-0"` for the 40px rule, with Edit / Move section / Remove. Keep the `<li>` itself inert so the kebab is the only hit target. Reuse the AddStudentDialog form body for Edit.
3. **"Move section" is not a PATCH on a section field** — no such field exists. `Student`'s only parent is `roster`. Resolve the destination roster via the file's existing `rosterForGroup(groupId)` helper and PATCH `{roster: destRosterId}`.
4. Handle `uniq_roll_per_roster`: both the roll edit and the move can 400 on collision. Surface `err.response.data.roll_number[0]` as an **inline field error** on the roll input, not a generic toast.
5. **Remove is not what it looks like.** All three FKs to Student are `on_delete=SET_NULL`, so DELETE does not remove past scores, it permanently orphans them. Check for existing results first; if any, the custom modal must say the student's past results will become unattributed, and preferably offer archive. Never `confirm()`.

**Why this ranks here:** the roll number is the key the sheet is printed and matched against, and `analytics/services.py:475` groups cross test history by `roll_number`, so a typo silently splits one student into two identities forever. The demo roster already carries 7 unremovable junk rows left by auditors, and sheet generation iterates the whole roster, so that junk burns paper and quota on every run.

---

### 10. Mobile navigation, and Review where the teacher actually is

**Files:** `/home/user/omr.doxaed.com/frontend/src/components/AppShell.jsx`, `/home/user/omr.doxaed.com/frontend/src/components/shell/nav-config.js`, `/home/user/omr.doxaed.com/frontend/src/routes/exam/ExamOverview.jsx`, `/home/user/omr.doxaed.com/frontend/src/routes/Scan.jsx`

1. `AppShell` already computes `panel` at line 803 and passes it only to `PrimaryRail` (`hidden ... lg:block`). Thread it: `<MobileDrawer panel={panel} />`. **Do not** call `usePanel()` inside `MobileDrawer` — it calls `useLocation`/`useOrg`/`useClass`/`useTest` and would double fetch. In the drawer body, above the static NAV block: `panel.back` as a back row, then `panel.groups.map(...)`, then a separator, then the existing NAV rows. This alone restores Roles, Usage, Billing, Organization settings on `/org/*` and all six lifecycle stages including Review on `/tests/*`.
2. Add the missing leaf inside the `role === "admin"` branch at `AppShell.jsx:255-258`: `{ label: "Audit log", to: \`/org/${s}/audit\`, end: true, icon: ScrollTextIcon }`. The page exists and nothing links to it **on either surface**.
3. `usePanel` returns null on `/classes` and other unscoped routes, so the drawer must not go empty. Give `nav-config.js`'s NAV a real workspace group (Classes, Folders, Scan) and an Organization section whose `to` is `/org/${slug}`. `flattenNavLeaves()` then feeds those same leaves into Cmd-K's "Go to" for free.
4. Bottom tabs: **Classes / Scan / Account**. `/scan` renders standalone with its own test picker. Organizations stays reachable via the drawer's OrgSwitcher.
5. Add the missing **Review** card to the `ExamOverview` Lifecycle grid with a pending count badge, and a "Review N flagged" link on `/tests/:id/scan` after an upload completes. This is the trust critical half: the low confidence queue produced by a phone scan is currently typed URL only on the device you scan from.
6. Close the Sheet when OrgSwitcher's "Manage organization" navigates (`AppShell.jsx:487-490` sets the popover's own open state but not the drawer's).

---

### 11. Two CSS lines that fix the answer key radio on every phone

**Files:** `/home/user/omr.doxaed.com/frontend/src/index.css`

`index.css:439` applies `min-height:40px` to every `button` under 768px, excluding only `[data-size='icon-xs']` and `[data-slot='tab-dot']`. Radix renders Checkbox, RadioGroupItem and Switch as `<button>`, so at 390px: Switch 32x18 → 32x40, Checkbox 16x16 → 16x40, RadioGroupItem 16x16 → 16x40. The answer key radio, the control that decides what the grader marks correct, renders as a 16px wide sliver. The rule does not even meet its own goal, since 16px and 32px wide targets still fail the 40px rule on the cross axis.

```css
/* line 439: extend the exclusion list */
button:not([data-size='icon-xs']):not([data-slot='tab-dot']):not([data-slot='checkbox']):not([data-slot='radio-group-item']):not([data-slot='switch']),

/* same @media block: grow the overlays the components ALREADY have */
[data-slot='checkbox']::after,
[data-slot='radio-group-item']::after { inset: -12px; }   /* 16 + 24 = 40 x 40 */
[data-slot='switch']::after { inset: -10.8px -4px; }      /* 40 tall, 40 wide */
```

No JSX change. All three components already carry `after:absolute after:-inset-x-3 after:-inset-y-2`; the overlay is just short on the vertical axis. Adding padding or a `::before` would double up and re-break sizing.

While here, invert the denylist to an allowlist keyed on `data-slot="button"`. It has already needed two exceptions and now needs three more; the next Radix primitive that renders as a `<button>` (toggle, slider thumb) inherits the same deformation silently.

**Verify at 390px** by asserting both the designed box and an `::after` rect >= 40x40. The seeded questions have no options, so the `/questions` repro must click "+ Add option" first or it passes vacuously.

---

### 12. Plan limits: visible before the click, recoverable after the failure

**Files:** `backend/omr/views.py:174-184`, `backend/organizations/views.py:196-203`, `/home/user/omr.doxaed.com/frontend/src/routes/OrgMembers.jsx`, `/home/user/omr.doxaed.com/frontend/src/routes/GenerateSheets.jsx`, `/home/user/omr.doxaed.com/frontend/src/components/ui/sonner.jsx`

**Do not touch `backend/billing/limits.py`.** It is a correct predicate service, and everything the UI needs is already exposed by `GET /billing/organizations/:id/plan/` (`billing/views.py:222` returns plan + limits + usage), already wired as `getPlan()` in `api/billing.js`, already consumed by `Usage.jsx`. The data exists; it is just not present at the point of action.

1. **Machine readable 403s.** Both views return only `{"detail": "<prose>"}`. Add `{"code": "seat_limit"|"students_per_generation_limit"|"generations_per_day_limit", "limit": n, "used": n, "upgrade_url": "/org/<slug>/billing"}`. Keep `detail` byte identical so existing tests and toasts pass.
2. **Show the cap before the click.** Both pages call `getPlan(orgId)` on mount. `OrgMembers.jsx`: "· 1 member" → "· 1 of 1 seats used", and disable Invite at the cap with a persistent "View plans" link. `GenerateSheets.jsx:516`: "10 of 10 selected · Free plan allows 10 per generation", and disable Generate at line 549 with the reason **rendered next to it, not on hover** (there is no hover on the phone this flow is designed for).
3. **Persistent failure where it happened.** `OrgMembers.jsx` `handleInvite` catch (line 123): `inviteError` state rendered inside DialogContent above the footer as a destructive bordered block with an "Upgrade plan" button, cleared on email change. **This is the more important half** — the dialog staying open with stale data and no error is what makes the failure invisible. `GenerateSheets.jsx` `handleGenerate` catch (line 260): `genError` banner mirroring the existing success banner at 560 to 590 in destructive tone.
4. **Toasts stop covering the mobile tab bar globally.** `sonner.jsx` has `position="bottom-right"` and no offset; the toast measures top 735.5 height 92.5 over a tab bar at top 787 height 57. Add `mobileOffset={{ bottom: "calc(var(--tabbar-h) + env(safe-area-inset-bottom) + 12px)", left: "12px", right: "12px" }}` and define `--tabbar-h: 57px` once on the shell that renders that nav so the two cannot drift. Sonner's `mobileOffset` applies below its 600px breakpoint, which is where `lg:hidden` shows the bar.

---

### 13. Close the public leaderboard hole

**Files:** `/home/user/omr.doxaed.com/backend/results/public_views.py`, `/home/user/omr.doxaed.com/frontend/src/routes/Results.jsx`

`portal_leaderboard` (line 209) checks published and `show_leaderboard` and **nothing else**. The access code check lives only in `portal_lookup` (line 158). Anyone with the link gets every student's name, score, rank and percentile even in access code mode.

Extract the code check into a helper, call it from `portal_leaderboard`, and require a short lived token issued by a successful lookup. Rewrite the toggle's helper text to state plainly that anyone with the link will see the full ranked list of names and scores, and default `show_names` off when `show_leaderboard` is on.

Same file, same pass, one line: rank is currently **dense** (counts distinct scores), so the last student in a class of 10 prints as "#5 of 10". Use competition ranking: `rank = 1 + count of students with a strictly higher score`.

---

## 3. Fix next

Grouped by theme. Real work, none of it blocks a teacher on a deadline.

**Print economics and the printed page**
- **Derive the answer column count from page width** instead of hardcoding 2 (`geometry.py:225-307`), and give each page its own row budget by deleting the `row_pitch = min(row_pitch, row_pitch_other)` line at `geometry.py:275`. Move the roll grid beside the header (`geometry.py:181-222`) to drop `answer_top_page0` from 406 to ~200. Replace the fixed `ANSWERS_PER_PAGE` arithmetic with a capacity walk and delete the constants at `geometry.py:38-39`. Net: 4 options gives ~136 questions on page 1 and ~152 after, versus 50. A 100 question test goes from 2 pages to 1. Update `tests_omr.py:145-158` and `tests_geometry_phase3.py:202`, which pin the old formula. Safe: the scanner reads each sheet's own stored `template_descriptor`, so printed sheets keep their coordinates and no migration is needed.
- **Instruction block on page 1** in the rectangle the rendered PDF proves is empty: x in [413, 787], y in [196, 380]. Do **not** put it in the right half of the header band; `_draw_section_headers` owns x >= 413 from y = 76 and would be overprinted on every competitive sheet. Six lines of Helvetica 7pt at 11px leading: fill the bubble completely in black or blue ballpoint; mark only one option per question; do not tick, cross or write outside the bubbles; do not fold, staple or tear the sheet; keep the four black corner squares and the code square clean. Add Date / Duration / Max marks / Invigilator fields in the same block. Hairline 0.5pt border only, and keep all new ink out of `x<100 or x>727` combined with `y<100 or y>1069` so it cannot compete with fiducial detection. `tests_branding.py` has byte identical golden assertions that this breaks; gate the pass on a flag or update the goldens deliberately in the same change.
- **Per page identity strip** (student name, Sheet ID, "Page N of M") on pages 2+, which currently carry no human readable identity at all.
- **Enlarge the QR** to ~28 to 30mm with error correction Q or H, and let the review UI recover a `no_qr` sheet by typing the 8 character Sheet ID already printed on page 1.
- **Ellipsize a long institution heading** at the real `BRAND_X_RIGHT=700` boundary; it currently prints straight over the top right fiducial. Enforce the same limit in the serializer with a visible warning before an admin prints 300 sheets.

**Scan and review workflow**
- `omr/tasks.py`: move the `from omr.scan.pipeline import process_scan_job` import **inside** the existing try/except. With `CELERY_TASK_ALWAYS_EAGER=True`, any import failure of the CV stack currently 500s the whole batch instead of failing the jobs individually with an error_reason the results board already renders. Wrap the module level `pyzbar` import in `align.py:23` with a `cv2.QRCodeDetector` fallback. Add a "System packages" block to `docs/DEPLOYMENT.md` (`libzbar0 libgl1 libglib2.0-0`) and an `AppConfig.ready()` smoke import. Re-save `backend/requirements.txt` as UTF-8; it is currently UTF-16.
- `Scan.jsx` `handleUpload` catch: persistent inline error card with a "Try again" button, not just a 5 second toast. Build the message defensively (`typeof err.response?.data === "string"` means an HTML or proxy body). **Field keyed 400s are currently swallowed** — the view returns `{"test": "Test not found in your account."}` and the catch only reads `.detail` and `.non_field_errors`, so a perfectly actionable error renders as "Upload failed". On status >= 500, warn that the batch may have partially processed and link to results: the POST reserves a ScanEvent before processing, so a blind retry duplicates the batch **and** burns a second scan against the monthly cap.
- **Kill the dead `test_mismatch` path.** `codes.py:36` builds an 8 hex prefix; `pipeline.py:531` does `uuid.UUID(hex=prefix)`, which always raises, so the branch at line 205 is unreachable for every sheet ever printed and execution falls through to a hard `status=failed` with `error_reason="sheet_not_found:8409ed44-45TWYP4F"` shown verbatim to the user. Delete `_parse_test_id_from_sheet_code` and resolve globally on `sheet_code` (which is `unique=True`), comparing the real FK. Unknown → needs_review + review item, never failed. Mismatch → needs_review + review item naming the other exam, **but only when that test passes the same `scope_filter`/`visibility_q` used in `ScanBatchSheetsView`**, otherwise a stray sheet leaks a rival tenant's exam name. Move `REASON_LABELS` out of `ReviewQueue.jsx:16-25` into a shared module so no machine token reaches a user anywhere. Fix `omr/tests_phase1b.py::TestMismatchTests` (currently 2 errors, UUID not JSON serializable) so this regression is actually caught.
- **Scan board banner tells the truth**: "X graded · Y need attention · Z could not be read", warning tone whenever Y+Z > 0. Return a per file `skipped` list naming files that could not be opened and why. Do not create the ScanEvent when total == 0. Reject HEIC and oversize files client side with a named list before upload.
- **Review cards need context**: student name and roll, exam title, the **1 based printed** question number, and a cropped image of that question's bubble row from the warped scan (`/omr/scan-jobs/<id>/warped/` and `bubble_geometry` already exist). Derive option labels from the sheet's `template_descriptor`.
- **Corrector**: it renders the scanned sheet 72px wide on desktop because it inherits `sm:max-w-sm`. Give it its own `max-w-5xl` dialog, image at >= 55% of width, zoom and pan, and a "jump to flagged question" control. Relabel "Mark correct bubbles per question" to "What the student marked" — the current label invites the teacher to enter the answer key as the student's answers. Show a live "Score will change from 2 of 10 to 5 of 10" line above Save. Raise option buttons from 32px to 40px to match ReviewQueue.
- **Roll reassignment is blind**: it attaches the sheet to any student in the whole account with that roll. Restrict the lookup to the rosters attached to this test, resolve as the teacher types, show the matched name for confirmation, and replace the free text field with a searchable student picker.
- **Sheet list and reprint**: generated sheets currently live only in React state, so a batch can never be reopened. Add a sheet list driven by `listSheets(test)` with per row print actions. Reprinting must not consume a generation. Warn before regenerating over sheets that already have a ScanJob or StudentResult, rather than silently overwriting their stored answer key.
- **Preview one sheet** server side without creating OmrSheet rows and without counting against quota. Nobody should spend a generation and a stack of paper to see what the sheet looks like.
- **Serve the batch PDF authenticated.** It contains every student's name and is currently served from `/media/` with no auth. Mirror `OmrTestQuestionPapersBatchView` and use the existing `downloadAuthedBlob` helper.

**Analytics correctness**
- **Item Analysis and option distribution aggregate by printed sheet position**, so psychometrics are computed over scrambled questions and contradict the Questions tab. Resolve `q_pos` through `omr_sheet.question_order` to the question id before aggregating in `compute_test_profile`, key items by question id, emit `order_index` and the stem. Option distribution must count **students**, not marks, with an explicit "No answer" row.
- **Analytics, ranks and report cards are cached and never recomputed** when a review item is resolved or a sheet is regraded. Call `recompute_test_profile` on both. Until then surface `generated_at` and a recompute action.
- **"Needs review: 0" is shown while every sheet sits unresolved in the queue.** Return the unresolved count from the results endpoint, render it in both badges, and gate "Share results publicly" behind a confirmation while items are open.
- **Improvement tab renders a zero height panel.** Delete the dead `hasChain` guard (`chain` always contains at least the test itself, so it can never fire) and branch on the server's own `trend === "insufficient_data"`, with a "Create a retest" action wired to the already exported `retest()`. Also gate the line chart on `lineData.length > 1` so no future case paints a single unconnected dot. Same pass: empty states for analytics on an ungraded test (currently a broken looking page with three enabled export buttons) and for a review queue on a never scanned test (currently claims "All caught up").
- **Report card reads like a debug dump**: em dashes, a bare percentile number, a page and a half of "Untagged". Replace dashes per owner rule 6, render "10th percentile (of 10 students)", collapse topic sections when everything is untagged. Add the marking scheme as a one line rule on every result surface ("+1 per correct, 0.25 deducted per wrong, 0 for blank") and render blanks as a neutral state, not a wrong answer cross.
- **Results table** has no sort, no search, no rank, and arbitrary row order that changes between loads. Sort by score descending with a stable secondary on roll, add sortable headers, rank and percentage columns, and a "needs review only" filter.

**Honesty of the sales and help surface**
- **Ship the topic field first** (~15 lines): add a Topic input to `frontend/src/features/test/QuestionEditor.jsx` and thread `topic` through the payload. The column exists, the serializer already lists it, `views.py:140` already copies it onto the sheet, `report_card.py` already computes topic averages and strengths, and `StudentDetail.jsx:24` already renders `TopicAccuracySection`. One input turns four already built, permanently empty analytics surfaces on. `QuestionEditor` is shared by both the wizard and `/tests/:id/questions`, so one edit covers both.
- **Then the copy sweep, all occurrences.** "Question bank" appears in `Help.jsx:20-21`, `landing/Hero.jsx:53`, `landing/Bento.jsx:19`, `landing/HowItWorks.jsx:11`, `landing/UseCases.jsx:20`, `landing/ProductGraphics.jsx:459`, `Features.jsx:21/26/121/144`, `BuiltForPage.jsx:50/52`, `FAQ.jsx:101`. There is no question bank model, route, endpoint or UI; `Question` is FK'd to `Test`, so reuse is structurally impossible, not merely unbuilt. Help step 1 currently sends every new user hunting for it. Do **not** soften "reuse across tests" into "reuse". Cross test ranking (`BuiltForPage.jsx:36/41`): every analytics route is keyed by `test_id`; leave `:67` alone, that one is true per test. Sectional papers is the one with real commercial exposure since `Pricing.jsx:136` ticks it on paid tiers; drop the row until `TestWizard` grows a section builder that POSTs to `/sections`.
- **Plan cards on the create-organization screen are invented and 5x looser than what the server enforces.** Render from `GET /api/v1/billing/plans/` in the enforced units.

**Question editor ergonomics**
- **Fix sticky at the root**: `AppShell.jsx:839` `main` has `overflow-auto` but never scrolls (`main.scrollHeight === main.clientHeight`), so any `sticky bottom-0` inside it can never detach. Give the AppShell flex root `h-dvh overflow-hidden` so `main.flex-1 overflow-auto` owns the scroll. Then `ExamQuestions.jsx:197`'s Save all bar starts working as written, everywhere, and so does every future sticky bar. Bump its z to >= 50 to clear the z-40 tab bar. Do **not** just swap sticky for fixed locally.
- **Seed four options**: `makeBlankQuestion(count = 4)`, with `ExamQuestions` passing `test?.default_options ?? 4` (the model default is already 4; `grep default_options frontend/src` returns zero hits). Add an "Options per question" stepper to wizard step 1 so the column stops being dead.
- **Collapse on save and on load**: set `collapsed: true` in `apiToEditor` and in `saveQ`/`saveAll` success. Takes the seeded page from 3362px to roughly 700px. Guard empty text with a "Question 3 (empty)" label so blank questions stay findable.
- Enter in the last option input saves and focuses the next question's textarea.

**Navigation, onboarding and shell polish**
- **Folders is billed and unreachable.** Add `matchFolderScope(pathname)` to `usePanel` returning the same org panel with a Folders item and a back link, delete the `folders.length > 0` guard at `NewClass.jsx:105` (without it the first folder is uncreatable), add a Folder select to `ClassSettings.jsx` (FolderDetail's empty state currently instructs users to use a control that does not exist), and move FolderDetail's "Back to folders" button out of the not found branch.
- **Retire Rosters rather than surfacing them.** `ClassStudents.jsx:34` states the model: each group keeps one hidden roster auto named "Students". Promoting them to the rail creates a competing way to manage students and exposes two indistinguishable "Students" rows. Delete the `/rosters` routes and the mislabeled `CommandMenu.jsx:149` "New roster" action; redirect `/rosters/:id` to the owning group's students page for deep links.
- Rename `GenerateSheets.jsx:446` "Roster" to "Class section" and point the empty state at `/classes/:id/students` rather than the class overview.
- **Route new users to the onboarding wizard that already exists and works** and that nothing links to. After login, if the user has zero orgs and no `ONBOARDED_KEY`, navigate to `/onboarding`.
- **Finish the wizard onto `/tests/:id`**, not the class overview, with Generate marked as next.
- **Scroll the generation success panel into view and focus it**; today the print buttons render below the fold and the page looks unchanged. Name downloads after the exam, not `question-papers.pdf`.
- Ask for sheet branding **once** and auto save it. It is asked twice and the second copy has its own Save button, so a toggle made just before generating is silently not applied.
- **Explain shuffle.** It is on by default with no explanation, and the primary print button prints only the answer sheets, so a shuffled batch is printed against a single shared question paper. Make "Download print packet" the primary action when shuffle is on.
- Set a real `<title>` (every tab currently reads "frontend") and a per route title hook. Render an in-app 404 inside the shell for signed in users instead of the marketing 404 inviting them to sign up. Replace raw UUID page subtitles on Results and Review with the test title.
- **Remove the gradients** (owner rule 4). Every logged out page including both auth screens paints radial glows; replace with flat tinted bands. Render `GoogleButton` only when `VITE_GOOGLE_CLIENT_ID` is set — it is currently the largest control on both auth pages, it is dead, and its failure message names an internal env var to the end user.
- Mobile typography and layout: lift `--text-xs` to 12px and `--text-sm` to 14px below 768px; start KPI grids at `grid-cols-2`; stack PageHeader below `sm` so titles stop truncating at 320px; pin dialog footers; give `DataTable` a `primaryColumn` heading and `onRowClick` instead of transposing the desktop table into label/value pairs.
- Mark "Roll number" as the required field in the Add student modal. It currently marks the optional field as optional and leaves the required one unmarked, so the first student a teacher adds fails to save.

**Governance**
- **Invite dialog has no scope field**, so every invited staff member silently gets org wide visibility of all students' results. Add a required Scope selector, create the RoleBinding with that `scope_group` on accept, and add an Access column to Members showing the resolved scope and the source of each grant. Warn when a narrower binding is added on top of an existing org wide one: the widest grant wins.
- Offer the full group tree in the Scope picker so a member can be scoped to a section or batch, not only a whole top level class.
- System roles open in a full editor with an editable name and live checkboxes that always rejects the save, and **all six shipped roles are system roles**. Render read only with a "Duplicate as custom role" primary button.
- Disable Remove for the last remaining owner.
- The audit log records nothing after a full session of real org changes. Either emit events for the writes that matter, or hide the page behind an explicit "coming soon" state.
- Registration ends on an empty login form and email verification is never enforced, never nudged and cannot be resent. Prefill the email at minimum; add a resend endpoint.
- Widen the public portal body from 27% of viewport to the standard shell, and handle 429 distinctly from 404 (a throttled portal currently tells students the teacher's link is broken).

---

## 4. Consciously skip

| Skip | Reason |
|---|---|
| **Create the Test only on Finish** (the obvious fix for ghost drafts) | `StepQuestions` saves each question via `createQuestion({test: testId, ...})` against a real server id (`TestWizard.jsx:541`). Deferring creation means buffering all questions client side, bulk posting them, rewriting StepQuestions and StepReview, and losing crash recovery. Delete solves the actual problem for two lines of code. |
| **A 24h server side sweep of empty drafts** | Unnecessary once delete exists, and it would silently destroy a teacher's half built exam over a weekend. |
| **Two students per A4 with a cut line** | Each half needs its own 4 fiducials and QR, and `pipeline.py`'s page model expects one 4 fiducial sheet per image. For any test of 50 questions or fewer the page count is already 1, so it saves nothing. All the print saving comes from columns per page. |
| **A layout selector on the Generate page** | The width derived column count needs no user decision. Do not make the teacher choose. |
| **Rosters as a rail section** | Rosters are deliberately internal (one hidden auto created roster per group). Promoting them creates a second competing student management surface and exposes two rows both named "Students". Retire instead. |
| **Building a question bank, cross test ranking, or sectional papers this cycle** | All three are real product bets, none is a bug. Fix the copy that sells them today; build them when they are on the roadmap. The pricing table ticking "Competitive / sectional" on paid tiers is the only piece with commercial exposure, and dropping the row costs one line. |
| **Editing `backend/billing/limits.py`** | It is a correct pure predicate service. Everything the UI needs is already returned by `OrgPlanView`. The only backend edit worth making is in the two views that emit the 403s. |
| **`DEBUG=False` plus a DRF exception handler as the fix for the scan 500** | `DEPLOYMENT.md:52` already requires `DEBUG=False`, and DRF's handler never sees an exception raised outside the view's call stack; a Django 500 is always HTML. The durable fix is moving the import inside the try in `tasks.py` and making the client defensive. |
| **A numbered jump rail in the question editor** | Redundant once questions collapse on save. Collapsed rows give you the index for free. |
| **Uncapping the student picker list to natural height** | 300 rows at 36px is a 10,800px page. Multi column plus search removes the trap; removing the cap moves it. |
| **A roster scoped student detail sheet** | `StudentDetail` already exists at `/tests/:testId/students/:studentId` as a test scoped analytics view. A second detail route duplicates it and adds a navigation layer. Edit in place with a row kebab. |
| **Printing a border rectangle inside the sheet margin as the primary alignment aid** | Good belt and braces later, but it is a print template change that invalidates every sheet already printed. The page crop fixes the same problem for sheets already in circulation. |
| **flow-01, "the whole grading path is dead"** | Rejected on verification and should not be resurrected. The running venv has `libzbar.so.0`, the endpoint returns JSON, `tasks.py` already catches pipeline exceptions, and 15 StudentResult rows exist. The real residue (libzbar0 undeclared in the repo, and `Scan.jsx` discarding field keyed 400s) is captured in Fix next. |

---

**Suggested sequencing.** Wave 1 = items 0 to 5 (scan trust). Wave 2 = items 6 to 9 (the data a teacher owns). Wave 3 = items 10 to 13 (surface, limits, security). Items 11 and 13 are each under an hour and can go out immediately regardless of wave.