# OMRFlow — Product v2: Folders & Sharing, Shuffled Question Papers, Sheet Branding, Inline Scan Correction, UX Overhaul

Status: PLAN (build-ready) — SECURITY CRITIQUE = NEEDS_REVISION; corrections below are AUTHORITATIVE.
Date: 2026-06-18

> ## ⚠️ SECURITY CORRECTIONS — AUTHORITATIVE (override the body where they conflict)
> The adversarial review found real issues. Implement these exactly:
>
> **S1 — Authenticated file serving (HIGH, also a CURRENT vuln).** `/media/` is served UNAUTHENTICATED
> (`config/urls.py` Django `static()`), so today's OMR `pdf_file` URLs — and the planned
> `question_paper_file` / `ScanJob.warped_file` (all PII-bearing) — are bearer URLs anyone can fetch.
> Serve them through AUTHENTICATED, scoped views (`GET /api/v1/omr/sheets/<id>/{pdf,question-paper}/`,
> warped-scan endpoint) that run `scope_filter & visibility_q` + object check then stream
> (FileResponse / X-Accel-Redirect). Frontend uses authenticated fetch (blob), not raw /media links.
> NEVER expose PII files via `/r/<slug>` or any AllowAny path. Test: anonymous GET of a file URL → 403/404.
>
> **S2 — Folder visibility must be enforced at EVERY query site, not just IsInScope (HIGH).** Object
> scope is scattered: `IsInScope.has_object_permission` only checks membership-exists (any active
> member passes any org row), and the child/list views (QuestionViewSet, SectionViewSet, StudentViewSet,
> StudentResult/ReviewItem/Resolve, OmrSheetListView, ScanBatchDetailView + the new Phase-4
> regrade/sheets endpoints) use bare `IsAuthenticated` + hand-rolled `get_queryset`/`get_object_or_404`
> on a scope_filter-ONLY queryset. Thread `visibility_q` (with the folder prefixes incl.
> `test__class_group__folder__`, `omr_sheet__test__class_group__folder__`,
> `scan_job__batch__test__class_group__folder__`) into ALL ~8 get_queryset/get_object_or_404 sites AND
> IsInScope. IDOR tests REQUIRED: a non-shared member cannot read/edit by id or via `?test=`/`?roster=`.
> Make "list-filter predicate == object-resolution predicate" a tested invariant.
>
> **S3 — answer_key must not leak to lower-trust surfaces (MEDIUM).** `OmrSheetSerializer` exposes
> `answer_key`/`template_descriptor`. Split serializers: full (owner/EDIT) vs restricted (VIEW-share
> consumers, the Phase-4 sheets response, any future student surface) — answer_key only to the owner/EDIT.
>
> **S4 — Branding is a header RE-LAYOUT, not "draw into whitespace" (MEDIUM).** `_draw_header` already
> uses x~76,y~76–141 and the competitive section legend uses x≈413,y~76. `_draw_branding` must reserve a
> sub-rect and push header text + section legend below/beside it — never overprint. Keep `HEADER_H` fixed
> (no per-sheet descriptor rebuild). Test: branding + competitive sections → no overlap + identical bubble coords.
>
> **S5 — Admin override + `request._membership` (MEDIUM).** `visibility_q`/`IsInScope` must call
> `get_active_org(request)` FIRST and read role from the returned membership explicitly — never assume
> `request._membership` exists (it's only a side-effect of get_active_org). Admin override is bounded to
> the ACTIVE org, READ by default, audit-logged.
>
> **S6 — Logo upload hardening (LOW→real DoS).** `Test.logo`/`Organization.logo` ImageFields need max
> file size, max dimensions, content-type allowlist, and a PIL `MAX_IMAGE_PIXELS` guard BEFORE
> `ImageReader` (decompression-bomb defense; the logo is drawn into every sheet).
>
> **S7 — Question-paper correctness (MEDIUM).** Renderer looks up each option's TEXT by its ORIGINAL
> label (from `option_order`) while printing the letter `chr('A'+i)`. Golden test: for a known seed the
> printed letter of the correct option == `answer_key[printed_pos]`. Papers are PII → authenticated serving (S1)
> + a retention/cleanup note for batch papers.
>
> **Phasing note:** Phase 4 (inline scan) ships before Phase 5 (folder visibility flip); its new
> endpoints MUST be built visibility_q-ready (forward-compatible), not scope_filter-only. The Phase-5
> data migration (keep existing classes loose vs seed an org-wide VIEW share) needs OWNER approval and
> tests for BOTH the seeded-open and tightened states. Drop the Folder parent self-FK in Phase 5 unless
> a share-inheritance strategy is specified (visibility_q can't walk the parent chain in a flat Q()).

Branch base: `main` (work on `habitquest/...`-style feature branches per phase)
Owner vision (verbatim distilled): signup → create ORG → add members → anyone can create a FOLDER (any name) and SHARE it to org members (ADMIN sees EVERYTHING) → members create a CLASS, add STUDENTS + SUBJECTS → any member picks class+subject and creates a TEST (name it, select OMR sheet type/mode, add Q+A, mark correct option) → GENERATE the OMR. If SHUFFLE is on, ALSO produce the per-student SHUFFLED QUESTION PAPER (so the teacher knows each student's order). Generation opens the LIVE PUBLIC RESULT page (shareable, anyone-with-link). ANALYTICS stays teacher-only. The OMR must support PROPER SPACING + optional HEADING + LOGO (logo placeable anywhere at the top); normal exams may just add questions and generate (branding optional). While SCANNING, fix scan errors INLINE. Best-possible UI/UX: production-grade ONBOARDING (short, precise, no walls of text), fully mobile-responsive (320→desktop), secure/encrypted where needed.

This is ONE integrated plan synthesizing four research streams (permissions/folders, generation/branding, scan/inline-correction, UX overhaul). Each phase is independently shippable and E2E-verifiable. Everything is backward-compatible and additive.

---

## 0. Confirmed baseline (verified against the codebase — DO NOT rebuild)

Verified files: `common/scope.py`, `common/permissions.py`, `common/viewsets.py`, `assessments/models.py`, `assessments/views.py`, `organizations/models.py`, `organizations/views.py`, `omr/models.py`, `omr/scan/pipeline.py`, `frontend/src/routes/*`, `e2e/run.mjs`.

ALREADY BUILT and reused as-is (the plan layers on top, never replaces):

- **Owner-scope isolation chokepoint.** Every tenant row extends `OwnerScopedModel` (nullable `user` XOR `organization`). `common/scope.py::scope_filter(request, prefix="")` returns `Q(organization=org)` in org scope or `Q(user=request.user)` in solo scope; `scope_kwargs()` stamps exactly one owner key; `parent_in_scope(value, request)` validates a parent FK is in scope. `ScopedModelViewSet.get_queryset` filters by `scope_filter`; `perform_create` saves `**scope_kwargs`. CONFIRMED: org scope filter is `Q(organization=org)` only — **today every active member sees/edits every row** (flat shared workspace). `created_by` is stamped on ClassGroup/Test/Roster/OmrSheet but referenced in ZERO querysets — metadata only.
- **Org/membership/roles (Phase 6).** `OrganizationMembership.role ∈ {admin, member}` governs ORG-MANAGEMENT only (`require_membership(request, org_id, role=ADMIN)` gates invite/role-change/audit/billing). It is checked NOWHERE in data scoping. `get_active_org(request)` reads `X-Organization-Id` header ONLY (no `?org=` fallback, CSRF-safe), verifies an ACTIVE membership, and caches `request._membership` (so `request._membership.role` is available with no extra query).
- **Per-student deterministic shuffle.** `omr/shuffle.py::build_sheet_plan()` seeded by `_derive_seed(test.id, student.id)`. Each `OmrSheet` row stores `question_order` (list[int], Question PKs in PRINTED order), `option_order` (`{str(qid): [orig labels in printed order]}`), `answer_key` (`{str(printed_pos): [printed letters]}`), `shuffle_version` (integer seed → regenerable identically), `template_descriptor`/`page_map`, `pdf_file`, `human_readable_code`. CONFIRMED via `omr/models.py`.
- **Public result portal `/r/<slug>`** (Phase 2D) — resolves strictly by slug to ONE Test, AllowAny, never touches folders/sharing. Auto-available after generation. Satisfies "live public page, anyone-with-link."
- **Teacher-only analytics + report cards** (Phase 2/5) — scoped, never public. Satisfies "analytics teacher-only."
- **Encrypted PII** — `common.encryption.EncryptedTextField` on `Student.full_name` (decryption implicit on scoped read).
- **OMR modes** — standard / roster pre-bubbled roll / competitive sections; Mode C rendering landing now (`2026-06-18-phase3-modec.md`).
- **Scan pipeline** — `ScanUploadView` → `ScanBatch` → per-page `ScanJob` → `process_scan_job`/`process_image` (`decode_qr → detect_fiducials → warp_to_canonical (827×1169) → to_binary → read_roll → read_answers`). `ScanJob.reads` persisted; `ReviewItem` per flag; `grade_sheet` re-grades from arbitrary `{q_pos:[marked]}` (already inline-correction-ready — only the write surface is missing). Frontend `Scan.jsx` polls batch and shows only counts (the "blind funnel" gap).
- **Frontend stack** — React + Vite + Tailwind v4 + shadcn/ui. CLAUDE.md rule: NO native `<select>`/`alert`/`confirm`/`prompt`; custom dialogs/toasts only; responsive 320→desktop.

Owner-vision items already satisfied (no new work, only verify): public-page-anyone-with-link; analytics-teacher-only; competitive sections (Mode C); encrypted PII. The plan's job is folders+sharing+admin-sees-all, shuffled question paper, branding, inline scan fix, and the UX/IA overhaul.

---

## 1. Security model — the load-bearing decisions (read before any phase)

The single biggest risk is the **default-visibility flip**. Today org scope = "everyone sees everything." Folders/sharing introduce intra-org partitioning, which silently REMOVES the incidental "admin sees all" and can either hide data members rely on or re-leak it. Therefore:

**One shared visibility predicate.** Add `common/scope.py::visibility_q(request, folder_prefix="")` next to `scope_filter`. It returns, in ORG scope, the union:
```
folder created_by == request.user
  OR folder has FolderShare(shared_with=request.user)
  OR folder has FolderShare(share_scope=ORG)
  OR request._membership.role == ADMIN   # full-org short-circuit
  OR folder IS NULL AND created_by == request.user   # loose-class policy (creator+admin only)
```
In SOLO scope it returns `Q()` (empty/no-op) — folders/sharing never apply solo. ADMIN short-circuit: `if org and request._membership.role == ADMIN: return Q()` (i.e. fall back to the unqualified `scope_filter`), bounded to the **currently active org only** via `request._membership`.

**ALL list filtering becomes** `scope_filter(request) & visibility_q(request)` in org scope; solo stays `scope_filter` untouched. **ALL object permission** (`IsInScope.has_object_permission`) gets the SAME union + admin bypass so retrieve/update/delete-by-id cannot bypass folder sharing (prevents list/object filter drift → IDOR).

**Child-chain propagation.** Question/Section (`test__`), Student (`roster__`), OmrSheet (`test__`) scope through parent prefixes today. Extend prefixes to include the folder predicate, e.g. `class_group__folder__...` / `test__class_group__folder__...`, so a member cannot reach a hidden question/student/sheet directly via `?test=`/`?roster=`.

**Cross-org isolation invariants (hard constraints, enforced in serializer + DB):**
1. A Folder and its ClassGroups MUST share the same owner scope — `parent_in_scope(folder, request)` on assignment + `CheckConstraint`/`clean()` that `folder.organization_id == class_group.organization_id` (and user side likewise). Never let a folder pull a class across the user-XOR-org boundary.
2. A `FolderShare` may ONLY grant within the folder's OWN organization — validate `parent_in_scope(folder, request)` AND that `shared_with` has an ACTIVE membership in `folder.organization` before saving. Reject cross-org grantees (the #1 leak vector). `UniqueConstraint(folder, shared_with)` + partial-unique for the single ORG-scope row.
3. Admin override reads role from `request._membership` (resolved from `X-Organization-Id` against an ACTIVE admin membership) ONLY — never client-supplied role, never another org. READ by default; admin writes gated behind the same explicit role check. Solo requests have no membership → override unreachable. Log admin cross-member access to `AuditLog`.
4. Loose classes (`folder IS NULL`) = creator + admin ONLY. Do NOT default null-folder to org-wide (silent re-leak). A data migration must set policy for existing rows (see Phase 1).
5. Header-only org resolution holds — folder/share endpoints reuse `get_active_org`; never add `?org=`/body org override.
6. Public portal `/r/<slug>` unchanged — verify new folder/branding fields are NOT exposed in any AllowAny serializer.
7. Student-bearing folder shares are PII-sensitive — VIEW-share consumers who are not the data owner still trigger implicit decryption, so treat any visibility bug as a PII exposure; prefer VIEW (read) shares and keep generated papers behind scoped views.

**Migration safety:** the visibility flip ships behind a data migration that, for backward compatibility, can optionally seed an org-wide `FolderShare(share_scope=ORG, permission=VIEW)` for every pre-existing folder OR keep existing loose classes creator-visible — decision recorded as an Open Question (see §6). All branding/paper fields are nullable/blank with defaults → safe additive migrations, no backfill.

---

## 2. PHASE-BY-PHASE ROADMAP (ordered by value + dependency)

Phasing principle: ship visual/system foundations first (zero E2E risk), then the two owner-CRITICAL backend artifacts (shuffled paper, branding) that the existing journey can adopt without breaking, then inline scan fix, then the larger IA (folders/sharing/onboarding), then polish. The Playwright E2E (`e2e/run.mjs`) is a single scripted journey keyed off accessible names/placeholders/headings — the GOLDEN RULE is **ADD or RESTYLE, never RENAME**; if a rename is unavoidable, update `run.mjs` in the SAME commit.

### Phase 0 — Design-system foundation (no behavior change, zero E2E risk)
**Goal:** consistency + product identity primitives so later phases reuse one system.
**Deliverables (frontend only, `frontend/src/components/ui/`):**
- Add `Badge` (variants `success|warning|error|info|neutral` mapped to existing `--color-*` tokens in `index.css`), `PageHeader` (title+subtitle+actions+breadcrumb), `Breadcrumb`, `Skeleton`, `DataList` (renders shadcn `<Table>` at ≥md, stacked cards at <md from the SAME row data), promote Dashboard's `StatCard`, `ActionMenu` (1 primary button + DropdownMenu overflow).
- Re-theme `index.css` oklch tokens: one brand primary + one accent (indigo/teal pair), real sequential `chart-1..5` scale (Analytics is greyscale today), distinct `--font-heading` weight/tracking. KEEP all token NAMES; change only values.
- Refactor inline badges (Results ScoreBadge/NeedsReviewBadge, TestList StatusBadge, ReviewQueue ReasonBadge, Scan "Published") to `Badge`. Replace emoji controls (✕ ▲▼ ✓✗ ⚠) with lucide icons (X, ChevronUp/Down, Check, AlertTriangle). Bump tap targets to ≥40px (ReviewQueue option buttons are 36px → 40px).
**Verify:** full E2E passes UNCHANGED (no role/name/placeholder/heading touched). Visual smoke at 320/375/768/1280.

### Phase 1 — App shell, nav & IA scaffolding
**Goal:** best-in-class responsive shell + active-state nav, no data-model change yet.
**Deliverables:**
- `ResponsiveNav`: DESKTOP (≥lg) persistent left SIDEBAR using existing sidebar tokens, grouped WORKSPACE (Home/Dashboard, Folders, Classes, Rosters) / RUN (Scan, Review) / ORG (Organizations, Members, Audit, Billing — admin-gated); top bar keeps OrgSwitcher + account menu + breadcrumb. MOBILE (<lg) top bar + hamburger opening the SAME sidebar as a Sheet/Drawer + bottom tab bar for Home/Classes/Scan/Results.
- `NavLink` + `aria-current` active states. Stop the full-page `window.location.reload()` on org switch (`App.jsx:60-74`) — switch context in React state + re-fetch via query invalidation (reload acceptable only as temporary bridge).
- KEEP brand text "OMRFlow" and existing link accessible names ("Classes", "Rosters", "Organizations"); ADD Dashboard + Scan links (do not rename existing).
**Verify:** E2E navigates by URL (`page.goto`), not nav clicks, so nav changes don't touch the journey. Assert Landing heading + `/login`, `/register`, `/dashboard` render. Manual nav sweep at 320/768/1280.

### Phase 2 — List screens responsive (Table → DataList)
**Goal:** every list screen mobile-safe without duplicating markup.
**Deliverables:** migrate Classes, TestList, Rosters, RosterDetail, Organizations, Results to `DataList` (table ≥md, cards <md). Collapse TestList's `w-72` 6-button row into ONE contextual primary ("Continue" → next logical step by `test.status`) + `ActionMenu` overflow. Results: cards on <md (roll+name+score badge+flag, tap to expand responses); per-question table only ≥md.
**E2E contract to PRESERVE (frozen names):** dialog placeholders "e.g. Class 8A"/"e.g. Class 10A"/"e.g. Asha Devi"/"e.g. 101"; button/link names "Create class", "Create" (exact), "Create roster", "Add student", "Generate sheets", "Scan", "Results", "Review", "Analytics", "Detail", "View", "Members"; roster Select trigger "Select a roster…"; the roll text on Results ("Roll: <roll>"). ActionMenu items keep each name intact.
**Verify:** full E2E green; mobile card sweep.

### Phase 3 — Shuffled question paper + sheet branding (owner-CRITICAL backend artifacts)
**Goal:** generation also emits the per-student shuffled question paper; OMR gains optional heading+logo, scanner-safe. Normal exams unaffected (everything defaults off).

**3A. Models / migrations (additive, nullable, no backfill):**
- `assessments.Test`: `sheet_heading = CharField(max_length=255, blank=True, default="")`, `logo = ImageField(upload_to="branding/logos/", null=True, blank=True)`, `logo_position = CharField(choices=[left,center,right], default="left")`, `brand_inherit_org = BooleanField(default=True)`.
- `organizations.Organization`: `logo = ImageField(upload_to="branding/org_logos/", null=True, blank=True)`, `default_sheet_heading = CharField(max_length=255, blank=True, default="")`. Resolution order at generate: Test.logo/heading → Org defaults → none (folder-level branding deferred; org covers shared-folder reuse).
- `omr.OmrSheet`: `question_paper_file = FileField(upload_to="omr_sheets/", null=True, blank=True)` next to `pdf_file`.
- `GenerateSerializer`: `emit_question_paper = BooleanField(default=False)` — auto-forced True when `shuffle_questions` or `shuffle_options` is True. Branding needs NO request flag (read from resolved Test/Org).
- Three migrations: assessments (Test branding), organizations (org branding), omr (`question_paper_file`). All safe additive.

**3B. Shuffled question paper renderer (`backend/omr/question_paper.py`):**
- `render_question_paper_pdf(sheet_meta, question_order, option_order, answer_key, questions_by_id, *, branding=None, include_answer_key=False) -> bytes` using ReportLab **Platypus** (SimpleDocTemplate + Paragraph/Spacer/Image/Table/KeepTogether) — NOT the low-level Canvas (prose wraps and is variable-height; no fiducials/QR on this doc, so coordinate rigor doesn't apply).
- Reconstruction (no new shuffle math — read the stored plan): build `q_by_id`, `opt_by_orig_label` per question; `for printed_pos, q_id in enumerate(question_order)`: emit `Q{printed_pos+1}. ` + text/image; for each `i, orig_label in enumerate(option_order[str(q_id)])`: printed letter `chr(ord('A')+i)` + option text/image. Edge cases: image-only/label-only options fall back to label; multiple-correct = list; competitive sections grouped by the descriptor's `q_start/q_end` headings. When shuffle is OFF, `question_order`/`option_order` are identity copies → same renderer yields a plain paper (no special-casing).
- Layout: header reuses the branding helper (heading + optional logo), then Student name + Roll No. + **Sheet ID (`human_readable_code`)** — the only stable link between paper, student, and scanned OMR. Body = numbered Q in printed order with printed-letter options, Spacer between questions, KeepTogether per question. Teacher answer-key appendix gated by `include_answer_key` (pull `answer_key[str(printed_pos)]`) — the teacher-only artifact "CRITICAL when shuffle is selected."
- Determinism: fixed producer, no timestamps (mirror `generator.py:411-413`) → reproducible bytes.

**3C. Branding draw pass on the OMR (`generator.py::_draw_branding(c, sheet, page_h_px)`, page 0 only):**
- INVARIANT: purely additive draw in header whitespace — NEVER changes any `cx/cy/r`, NEVER reflows `template_descriptor` (the "C2 invariant" already enforced by `_draw_section_headers`). Scanner reads geometry from the stored descriptor, so branding is byte-identical to detection.
- Safe zone (geometric proof): header band `HEADER_H=168px`; TL fiducial center 52px from edges; QR is a fixed 80px block at top-right starting x≈707; roll grid starts y=188px. Branding rectangle = `x∈[76,700], y∈[40,150]` on page 1 — disjoint from all four. HEADING (Helvetica-Bold) at top of band; if present, push the institution/test/subject block down OR replace `institution`, keep text x≥76, y<164. LOGO via PIL `ImageReader` (same as QR draw), honor `logo_position ∈ {left,center,right}` but CLAMP to the rectangle, cap height ~40-48px, preserve aspect ratio; "right" stops before x=707.
- If the owner wants MORE generous spacing: the clean lever is bumping `HEADER_H` (geometry.py:29) — but that requires re-deriving AND re-storing the descriptor per sheet (scanner reads the descriptor, not constants). PREFER keeping `HEADER_H` fixed and fitting branding in the existing band. Never change a rendering constant without regenerating the descriptor (the one desync path).
- Pass-in: extend the per-student `sheet_dict` (views.py:295-305) with `heading`, `logo_path`/`logo_bytes`, `logo_position` from resolved Test→Org fields.

**3D. GenerateView wiring (`omr/views.py`):**
- Resolve branding (Test→Org) once before the loop; inject into each `sheet_dict`.
- In the per-student loop (alongside the existing OMR render+`pdf_file.save`): when `emit_question_paper` (or shuffle), `render_question_paper_pdf(...)` → `omr_sheet.question_paper_file.save("omr_sheets/{sheet_code}-paper.pdf", ...)`; collect `per_student_papers`.
- After the OMR batch merge (PyMuPDF/fitz loop, views.py:342-360), merge the paper batch → `omr_papers/{test.id}-{uuid}.pdf` via `default_storage`; add `batch_paper_url` to the response next to `batch_pdf_url` (transient, no model field, same as `batch_pdf_url` today).
- Serializers: `OmrSheetSerializer.question_paper_url` (SerializerMethodField mirroring `get_pdf_url`); add branding fields to `TestSerializer` (ImageField like Question.image/Option.image); add an org-settings serializer for org branding.
- PII: the generated paper renders student names → treat `question_paper_file` as PII-bearing, served via scoped views ONLY (never the public `/r/<slug>`).

**3E. Frontend Generate panel:** redesign `GenerateSheetsDialog` (TestList.jsx:57-189) into a Generate panel/route with roster picker, shuffle toggles, AND a Branding section (optional Heading text input + Logo upload + position picker left/center/right), branding optional/default-off. On success show TWO clearly separated downloads: "OMR sheets PDF" and (when shuffle on) "Shuffled question papers (per student)". Add a print-preview thumbnail with proper spacing before download.
**E2E contract to PRESERVE:** keep the "Generate" button (exact) and success text "Sheets generated successfully!" (run.mjs:220). The shuffled-paper link is an ADDITIONAL element. Branding default-off → existing journey unaffected.
**Verify (new tests):** existing `tests_geometry_phase3.py`, `tests_scan.py`, `tests_grade_phase3.py` pass UNCHANGED (branding additive). ADD a test asserting `render_sheet_pdf` with branding vs without yields the SAME descriptor + same bubble coords. ADD a test that `render_question_paper_pdf` reconstructs printed order from the stored plan (printed letters match `option_order`; answer-key appendix matches `answer_key`). ADD an API test that shuffle=true forces `emit_question_paper`. E2E: Generate flow still hits "Sheets generated successfully!"; assert the new shuffled-paper download link appears when shuffle on.

### Phase 4 — Inline scan correction (owner-CRITICAL UX)
**Goal:** turn the blind scan funnel into upload+verify+correct on ONE screen; re-grade on save. Review queue degrades to an optional "needs attention" filter over the same corrector.

**4A. Backend — expose per-sheet reads in the batch:**
- New `GET /api/v1/omr/scan-batches/<id>/sheets/` (or nest jobs in `ScanBatchDetailView`) returning per-sheet correction objects: `{scan_job_id, omr_sheet_id, sheet_code, page_no, status, confidence, error_reason/flags, student:{id,name,roll}, detected:{roll, answers:{q_pos:{marked,flag}}}, answer_key (teacher-side), student_result:{id,score,needs_review} if graded, image_url(s), open_review_item_ids}`. Source: `ScanJob.reads` (already stored) + `OmrSheet.answer_key` + `StudentResult`. New `ScanJobSerializer`/`SheetReadSerializer`. Keep `scope_filter(test__)` (and the Phase-5 folder predicate) on every query.

**4B. Backend — edit-reads / re-grade endpoint (core of inline correction):**
- `POST /api/v1/omr/sheets/<omr_sheet_id>/regrade/` body `{answers:{q_pos:[labels]}, roll?, student_id?}`. It: scope-checks via `test__`; validates `q_pos` in range and labels against the sheet's option set; writes corrected reads (update `ScanJob.reads` and `QuestionResponse.marked_options` for the WHOLE sheet, not just the first flagged question); calls `grade_sheet(omr_sheet, corrected_reads)` and persists `StudentResult` + `QuestionResponse`s via a REFACTORED shared persist helper (extracted from `_maybe_grade`/`_recompute_student_result` to avoid drift); auto-resolves ALL open `ReviewItem`s for that sheet (`resolved=True`, `resolved_by`, `resolution` snapshot) and recomputes `needs_review`; optionally reattaches a `no_qr`/failed `ScanJob` to an OmrSheet (set `omr_sheet`, `student`) before grading. This GENERALIZES the existing per-flag resolve (results/views.py) which edits only the FIRST flagged response.
- Do NOT double-charge the scan gate on edit (no new `ScanEvent`). Keep encrypted PII flowing through serializers, not raw.

**4C. Backend — warped crop / detected-marks context:**
- Persist the warped canonical PNG per job (`ScanJob.warped_file`) during `process_scan_job` (today the warp is discarded; only the raw upload is saved on `ScanJob.image_file`). RECOMMENDED: return the warped image URL + the descriptor's answer-bubble `cx/cy/r` geometry (already on `template_descriptor` via `OmrSheetSerializer`) so the frontend overlays marks itself (cheaper than per-question crop URLs). SECONDARY: emit per-question fill-ratio/confidence in `ScanJob.reads` (read.py keeps only marked+flag today) so the UI can rank low-confidence rows.

**4D. Frontend — "Scan & Verify" workspace (`Scan.jsx` rebuild):**
- Upload zone: keep test Select + file picker; add drag-and-drop, mobile camera capture (`accept="image/*" capture="environment"`), thumbnail strip.
- Live results board (replaces the progress-only card): as polling reports finished sheets (via the new per-sheet endpoint), stream SHEET CARDS with student/roll/score + status chip (Clean green / Needs attention amber / Unresolved error red); flagged-first; summary header ("18 scanned, 15 clean, 3 need attention"); filter toggle All / Needs-attention-only.
- Inline corrector (drawer on desktop, full-screen on mobile): LEFT = warped sheet image with detected marks overlaid (filled=green ring, double-mark=amber, faint=dashed amber, blank=grey) using descriptor bubble geometry; RIGHT = per-question grid, each row = Qn + detected option(s) preselected as the A–F toggle group (REUSE ReviewQueue.jsx's custom button group — NEVER a native select) + confidence/flag badge + subtle answer-key indicator; flagged rows pinned/outlined amber; roll+student editable (roster dropdown) for no_qr/roll_mismatch. SAVE → single `regrade` call re-grades the whole sheet, updates the card score in place, auto-resolves ReviewItems. "Approve & next"/"Next flagged" keyboard loop; "Approve all clean" bulk; manual-entry fallback (blank grid + sheet_code/student picker) for no_qr/alignment hard failures.
- API layer `api/scan.js`: add `getBatchSheets(batchId)` and `correctSheet(omrSheetId, {answers, roll, student})` alongside `uploadScan`/`getBatch`.
**E2E contract to PRESERVE:** keep `input[type=file]` (run.mjs:239 setInputFiles), "Upload & scan" button name, completion text containing "processed successfully" (run.mjs:241). Keep `/review` route + its "Resolve" button and reason text "Roll number mismatch" (run.mjs:338) for the Mode-B tamper test.
**Verify (new tests):** API test for `regrade` editing arbitrary questions + whole sheet, auto-resolving ReviewItems, no double-charge. Test the shared persist helper parity with `_recompute_student_result`. E2E: existing scan journey still reaches "processed successfully"; ADD a step that opens a flagged sheet, corrects an option, saves, and asserts the score/needs_review updates.

### Phase 5 — Folders + sharing + admin-sees-all (the IA backbone) + subjects + onboarding
**Goal:** the owner's org→FOLDER→class→subject→test IA, intra-org sharing, explicit admin override, and short onboarding. This is the highest-risk phase (the visibility flip) — ship it last among the substantive phases, behind a careful data migration.

**5A. Models / migrations:**
- New `folders` app. `Folder(OwnerScopedModel)`: inherits `user` XOR `organization` + timestamps; add `created_by = FK(AUTH_USER_MODEL)`, `name = CharField`, `parent = FK('self', null=True)` (nesting later).
- `FolderShare`: `folder = FK(Folder)`, `shared_with = FK(AUTH_USER_MODEL, null=True)` (member grant), `share_scope = CharField(choices=[MEMBER, ORG])` (ORG = whole-org, shared_with null), `permission = CharField(choices=[VIEW, EDIT])`, `created_by`, `created_at`. `UniqueConstraint(folder, shared_with)` + partial-unique for the single ORG-scope row.
- `assessments.ClassGroup`: add `folder = FK('folders.Folder', null=True, blank=True, on_delete=SET_NULL, related_name='class_groups')` (null = "loose"/root class, preserves existing rows). ClassGroup STAYS OwnerScoped — folder is an organizing+sharing layer ON TOP, never a replacement. Add `CheckConstraint`/`clean()` enforcing `folder.organization_id == class_group.organization_id` (and user side).
- SUBJECT as an entity: add a `Subject` per class (class has subjects; a test is created from class+subject). KEEP backward-compat — `Test.subject` free-text remains a fallback if no subjects defined (so TestWizard's "e.g. Mathematics" placeholder/flow is unchanged).
- Question/Section/Student/OmrSheet need NO model change — they scope through Test/Roster → ClassGroup → optional Folder.

**5B. Scoping / permission changes (the core):**
- Implement `visibility_q(request, folder_prefix="")` in `common/scope.py` per §1.
- `ClassGroupViewSet`/`TestViewSet`/`RosterViewSet` `get_queryset`: in org scope use `scope_filter(request) & visibility_q(request, <prefix>)`; solo scope stays `scope_filter`. Child viewsets extend prefixes (`class_group__folder__`, `test__class_group__folder__`).
- `IsInScope.has_object_permission`: tighten the member path to the visibility union; ADD the admin short-circuit (`request._membership.role == ADMIN` in the active org → True). EDIT vs VIEW: list/retrieve allowed for any visibility grant; create/update/delete on a class require EDIT (folder owner OR EDIT share OR admin).
- New `FolderViewSet` + `FolderShareViewSet` (scoped, header-only org). Share writes validate `parent_in_scope(folder)` AND `shared_with` ACTIVE membership in `folder.organization` (reject cross-org). Log admin cross-member access to `AuditLog`.
- Endpoints: `GET/POST /api/v1/folders/`, `GET/PATCH/DELETE /api/v1/folders/<id>/`, `GET/POST /api/v1/folders/<id>/shares/`, `DELETE /api/v1/folders/<id>/shares/<sid>/`; ClassGroup gains `?folder=<id>` filter and a `folder` write field validated by `parent_in_scope`.

**5C. Data migration (the visibility flip):**
- Decide loose-class policy = creator+admin ONLY (recommended). For existing rows, EITHER (a) keep them loose (members lose the flat-pool view they had — disruptive) OR (b) seed one org-wide `FolderShare(share_scope=ORG, permission=VIEW)` per existing folder and/or place existing classes in a default shared folder to preserve current "everyone sees" behavior during transition. RECORD the choice as an Open Question (§6) — owner must approve before this migration runs.

**5D. Frontend IA + onboarding:**
- `/folders` and `/folders/:id` routes: a folder contains classes; sharing UI = membership list with VIEW/EDIT; admin "All folders" toggle.
- Breadcrumb (Org / Folder / Class / Subject / Test) on every deep screen via the shared `Breadcrumb`+`PageHeader` (replaces 3 hand-built header variants). "Test progress" rail (Build→Generate→Scan→Review→Results→Analytics) on test-scoped pages (reuse Stepper styling) replacing the 6-button row.
- Subject as a selectable entity per class (free-text fallback preserved).
- Onboarding `/onboarding` (gated by Dashboard's existing `isNewUser` signal + a localStorage/profile completion flag): full-screen wizard, 3-dot Stepper, persistent "Skip for now". STEP 0 Welcome (1 screen, "Get started"); STEP 1 Create organisation (org name, "Create organisation", inline "Just me for now" → Personal context, reuse `createOrg`); STEP 2 Invite members (chips multi-email + role select, "Send invites"/"Skip"); STEP 3 First class (name, "Create class", reuse `createClass`, one-line hint); STEP 4 First test (two cards: "Start blank" → TestWizard / "Skip"). Completion → Dashboard one-time "Workspace ready" banner. COPY RULE enforced: ≤1 heading + 1 ~6-word helper per step, verb button labels, single-line inline errors.
**E2E safety:** gate onboarding redirect behind new-user signal AND localStorage flag so direct-URL E2E steps bypass it; OR add explicit onboarding steps to `run.mjs` using the new headings/labels. Keep TestWizard's "e.g. Mathematics" placeholder/flow unchanged (subject free-text fallback).
**Verify (new tests — REQUIRED per CLAUDE.md for scope isolation):** (1) member sees only creator+shared+org-share folders; non-shared folder's classes/tests/rosters/children invisible in list AND via direct `?test=`/`?roster=`/by-id (no IDOR). (2) admin sees full org pool (override) but NOT another org's data (bounded to active `X-Organization-Id`). (3) cross-org `FolderShare` grantee rejected; folder↔class scope-mismatch rejected. (4) solo scope unchanged (no folders/sharing). (5) loose-class policy = creator+admin. (6) EDIT vs VIEW enforced on create/update/delete. (7) list-filter and object-permission use the SAME predicate (retrieve/update/delete-by-id cannot bypass sharing). E2E: add folder create/share steps OR confirm bypass flag; full journey green.

### Phase 6 — Polish pass
**Goal:** final consistency + responsiveness sweep.
**Deliverables:** Skeletons replace every "Loading…" (Classes/Rosters/TestList/Results/Analytics/ReviewQueue); standardize `EmptyState` (replace hand-rolled empties in Results/ReviewQueue) with icon + one-line guidance + single primary action; consistent error state with retry (today failures only fire a toast → blank page); Analytics TabsList horizontally scrollable on mobile, charts verified legible at 320px, StatCards 2-up on mobile; TestWizard Stepper → compact "Step 2 of 3" + dots under md, sticky Next/Back footer; PublicResult single-column large-touch verify; final 320/375/768/1280 sweep.
**Verify:** full E2E across chromium/chrome/edge + modeB; visual regression sweep.

---

## 3. Owner-vision coverage matrix

| Owner requirement | Phase | How |
|---|---|---|
| Signup → create org → add members | reuse + 5 | Phase 6 orgs exist; onboarding wizard (5D) makes it the first-run path |
| Anyone creates a FOLDER, shares to org members | 5 | `Folder` + `FolderShare(MEMBER/ORG, VIEW/EDIT)` |
| ADMIN sees EVERYTHING | 5 | explicit admin short-circuit in `visibility_q` + `IsInScope`, bounded to active org, audit-logged |
| Cross-org isolation preserved | 5 (+§1) | parent_in_scope + CheckConstraint + grantee-membership validation + header-only org |
| Class + students + subjects under folders | 5 | ClassGroup.folder FK; Subject entity (free-text fallback) |
| Create TEST: name, select OMR mode, Q+A, mark correct | reuse | TestWizard + modes (standard/roster/competitive Mode C) already built |
| GENERATE OMR | reuse + 3 | existing generator + branding pass |
| SHUFFLE → per-student shuffled question paper | 3 | `question_paper.py` reconstructs printed order from stored plan; per-student + batch PDFs |
| Quick no-branding "just questions → OMR" | 3 | `emit_question_paper` defaults False; branding fields blank → OMR only |
| LIVE PUBLIC result page, shareable, anyone-with-link | reuse | `/r/<slug>` (Phase 2D); surface "Copy public link/QR" after first results |
| ANALYTICS teacher-only | reuse | scoped analytics, never public — verify (§0) |
| OMR proper spacing + optional heading + logo (anywhere at top) | 3 | `_draw_branding` in clamped header safe-zone; HEADER_H lever if more spacing |
| Branding optional for normal exams | 3 | read from Test→Org; blank = no branding, no request flag |
| Fix scan errors INLINE | 4 | per-sheet reads endpoint + `regrade` endpoint + Scan & Verify corrector |
| Best UI/UX, mobile 320→desktop | 0,1,2,6 | design system + ResponsiveNav + DataList + polish |
| Production-grade onboarding, minimal text | 5 | `/onboarding` crisp 5-step wizard, enforced copy rules |
| Secure / encrypted where needed | reuse + all | EncryptedTextField PII; papers behind scoped views; visibility security model (§1) |

---

## 4. Security risk register (must-fix gates, from research)

1. **Cross-org FolderShare grant (highest):** validate grantee ACTIVE membership in `folder.organization`; reject otherwise. Phase 5 test required.
2. **Folder↔class scope mismatch:** CheckConstraint/clean `folder.organization_id == class.organization_id` + parent_in_scope on assignment. Phase 5.
3. **Default-visibility regression:** explicit loose-class policy (creator+admin) + data migration; owner-approved. Phase 5C.
4. **Admin override over-reach:** role from `request._membership` against active `X-Organization-Id` ONLY; bound to active org; audit-log. Phase 5.
5. **List/object filter drift → IDOR:** ONE shared `visibility_q` used by both `get_queryset` and `has_object_permission`. Phase 5.
6. **Child-chain propagation:** extend folder predicate into `test__`/`roster__`/`class_group__folder__` prefixes. Phase 5.
7. **Header-only org resolution holds:** folder/share endpoints reuse `get_active_org`; no `?org=`/body override. Phase 5.
8. **Public portal unchanged:** verify folder/branding/paper fields never appear in AllowAny responses. Phase 3 + 5.
9. **Encrypted PII scope:** generated papers PII-bearing → scoped views only; prefer VIEW shares; visibility bug = PII exposure. Phase 3 + 4 + 5.

---

## 5. E2E binding contract (frozen — ADD/RESTYLE, never RENAME; else update run.mjs same commit)

- Headings: "Grade a stack of bubble sheets…" (Landing), "Welcome back" (Dashboard), "Analytics".
- Texts waited on: "Email verified", "Class created", "Roster created", "Student added", "Sheets generated successfully!", "processed successfully", "Score distribution", "reliability|graded students", "Roll: <roll>", "Roll number mismatch".
- Button names: "Create account", "Sign in", "Create class", "Create"(exact), "Create roster", "Next: Add questions", "+ Add question", "+ Add option", "Save question", "Next: Review", "Finish & mark ready", "Add student"(exact), "Generate sheets", "Generate"(exact), "Upload & scan", "Export CSV/Excel/PDF", "Download all report cards", "Get result".
- Link/tab names: "Detail" (link), "Item Analysis" (tab).
- Placeholders: "Jane Smith", "you@example.com", "••••••••", "e.g. Mid-term Exam", "e.g. Mathematics", "e.g. Class 8A", "e.g. Class 10A", "e.g. Asha Devi", "e.g. 101", "Option A/B/C/…", "Select a roster…", "Select a test…".
- Locators: `#q-text-{i}`, `#q{i}-opt0-radio`, `#mode-roster`, `#roll_number`, `input[type=file]`, `div.rounded-xl.border` (question card — keep div+rounded-xl border or update selector).
- Routes: `/`, `/register`, `/login`, `/dashboard`, `/classes`, `/classes/:id`, `/classes/:id/tests/new`, `/rosters`, `/rosters/:id`, `/tests/:id/scan`, `/tests/:id/results`, `/tests/:id/review`, `/tests/:id/analytics`, `/r/:slug`.
- RECOMMENDED (separate commit, owner approval): harden `run.mjs` with `data-testid` hooks so future visual changes stop depending on copy/structure.

---

## 6. Open questions (need owner decision before the gated phases)

1. **Existing-data visibility flip (Phase 5C):** on rollout, do we (a) keep existing classes loose = creator+admin only (members lose today's flat-pool view), or (b) auto-seed an org-wide VIEW share / default shared folder to preserve current "everyone sees everything"? Recommend (b) for non-disruptive transition, then let owners tighten.
2. **Admin write override:** should admins also EDIT all org data, or READ-only by default with edit gated separately? Research recommends READ-by-default.
3. **Folder-level branding:** deferred (org+test cover the reuse case) — confirm acceptable, or pull folder branding into Phase 3.
4. **Subject migration:** promote `Test.subject` free-text into the new `Subject` entity for existing tests, or leave legacy tests on free-text indefinitely?
5. **More generous OMR header spacing:** keep `HEADER_H=168` fixed (branding fits the existing band, no descriptor rebuild) vs bump `HEADER_H` (requires per-sheet descriptor regenerate + re-store). Recommend keeping fixed unless the owner explicitly wants a taller header.
6. **Onboarding in E2E:** set the completion flag to bypass (simplest, journey unchanged) vs add explicit onboarding steps to `run.mjs`.
