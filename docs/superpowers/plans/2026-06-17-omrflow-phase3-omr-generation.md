# OMRFlow Phase 3 (Roster & OMR generation) Implementation Plan

> Standalone repo `projects/omr.doxaed.com/` (own `.git`), branch `phase-3`. Paths relative to repo
> root (`backend/...`). Commit to THIS repo. TDD; `- [ ]` steps. venv: `backend/.venv` (call
> `.\.venv\Scripts\python.exe` by path from inside `backend/`).

**Goal:** A solo user defines a roster (named+roll OR count-only), then generates a deterministic,
print-ready A4 PDF of personalized OMR sheets (QR + fiducials + roll-number dot grid + shuffled
answer grid), with the per-sheet geometry (`template_descriptor`) and answer key stored for the
Phase-4 scanner. Free-tier gates enforced.

**Architecture:** `rosters` app (Roster, Student) + `omr` app (OmrSheet + the engine). The engine is
pure-Python modules — `geometry` (builds the canonical-pixel template descriptor), `shuffle`
(deterministic per-student question/option order + answer key), `codes` (sheet_code), `generator`
(ReportLab renders the descriptor to a multi-page PDF, draws the QR via the `qrcode` lib). A
generation endpoint batches all students into one PDF and persists each OmrSheet.

**Tech:** Django 5 + DRF; ReportLab 4.5 (PDF), qrcode (QR), Fernet/`cryptography` (PII), PyMuPDF
(`fitz`) + pyzbar (QR round-trip TEST only). React (Vite, JS) + shadcn.

## Locked decisions
- **D1 Sheet:** A4 portrait. Canonical template raster = **100 DPI** → 827×1169 px, **top-left origin**
  (image convention). The descriptor stores all positions in these template pixels; the generator
  maps px→ReportLab points: `x_pt = x_px/100*72`, `y_pt = (H_px - y_px)/100*72`.
- **D2 Fiducials:** 4 solid black squares (side 24px) centered ~36px inside each corner. Their centers
  are the registration anchors stored in the descriptor.
- **D3 QR:** top band, encodes the compact string `"{sheet_code}|{page}|{total}"`. Also print a short
  human-readable code. QR drawn as an image via the `qrcode` lib.
- **D4 Roll grid (page 1 only):** N digit-columns × 10 rows (0–9) of bubbles; N = `max(2, digits of
  the largest roll_number in the roster)` (default 3). Descriptor stores origin + column pitch + row
  pitch + bubble radius.
- **D5 Answer grid:** 2 columns of questions/page; each question = number + option bubbles A..(A+num_options-1).
  Rows per column = `ANSWER_ROWS_PER_COL = 25` → 50 q/page; overflow to more pages with continuous
  numbering. `num_options` = the test's max options across its questions (clamped 2–6).
- **D6 Shuffle:** per sheet, `random.Random(seed)` where `seed = OmrSheet.shuffle_version` (a stored
  int). Persist `question_order` (list of question IDs in printed order), `option_order` (dict
  question_id→list of original option labels in printed order), `answer_key` (dict printed-position→
  list of printed option labels that are correct). Generation is fully reproducible from these.
- **D7 sheet_code:** `f"{test_id:06d}-{token}"` where token = 8 url-safe base32 chars (deterministic per
  sheet via the seed, unique). human_readable_code = the token. Globally unique (DB unique).
- **D8 PII:** `Student.full_name` uses a Fernet-`EncryptedTextField` (key `FIELD_ENCRYPTION_KEY` from
  env). roll_number stays plaintext (used for lookup). Names are never queried.
- **D9 Free-tier gates:** ≤10 students per generation, ≤5 generations/day (per user). Enforced
  server-side in the generation view; over cap → 403 with an upgrade message.
- **D10 Scope:** Roster is `OwnerScopedModel` (ScopedModelViewSet). Student + OmrSheet are CHILD-SCOPED
  (Student→roster, OmrSheet→test) → `IsAuthenticated` + queryset filtered through the parent's scope
  (per the child-scope pattern in current-state.md). Validators ensure FK parents belong to the user.

## File structure
- `backend/common/encryption.py` — `EncryptedTextField`.
- `backend/rosters/models.py` — Roster, Student. `serializers.py`, `views.py`, `urls.py`.
- `backend/omr/models.py` — OmrSheet. `codes.py`, `geometry.py`, `shuffle.py`, `generator.py`,
  `serializers.py`, `views.py`, `urls.py`.
- Tests: `rosters/tests_rosters.py`, `omr/tests_omr.py` (determinism, QR round-trip, gates, scope).
- Frontend: `src/api/omr.js`, `routes/Roster*.jsx`, generate flow.

---

## Task 1: PII field + Roster/Student models + endpoints (TDD)
**Files:** `backend/common/encryption.py`, `backend/rosters/{models,serializers,views,urls}.py`,
`backend/config/{settings,urls}.py`, `backend/.env(.example)`, `rosters/tests_rosters.py`.

- [ ] **Step 1:** Ensure `cryptography` is installed: `.\.venv\Scripts\python.exe -m pip install cryptography` then `pip freeze > requirements.txt`. Generate a key once: `.\.venv\Scripts\python.exe -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` and put it in `backend/.env` as `FIELD_ENCRYPTION_KEY=<key>`; add a placeholder line to `.env.example`. In `settings.py`: `FIELD_ENCRYPTION_KEY = env("FIELD_ENCRYPTION_KEY")`.
- [ ] **Step 2:** `backend/common/encryption.py`:
```python
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models


def _fernet():
    return Fernet(settings.FIELD_ENCRYPTION_KEY.encode())


class EncryptedTextField(models.TextField):
    """Transparently Fernet-encrypts text at rest. Not queryable by value (ciphertext varies)."""

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is None:
            return value
        return _fernet().encrypt(value.encode()).decode()

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        try:
            return _fernet().decrypt(value.encode()).decode()
        except (InvalidToken, ValueError):
            return value  # tolerate legacy plaintext
```
- [ ] **Step 3 (red) tests** (`rosters/tests_rosters.py`): roster CRUD scoped to user; student full_name encrypted at rest (raw DB column is NOT the plaintext) but reads back decrypted; count-only mode creates N students; roll_number unique within roster; cross-tenant roster 404. (Use the `ClassApiTests`-style throttle-clearing + `_auth`.) Key encryption test:
```python
    def test_full_name_encrypted_at_rest(self):
        from rosters.models import Roster, Student
        from django.db import connection
        r = Roster.objects.create(created_by=self.user_obj, user=self.user_obj, name="R")
        s = Student.objects.create(roster=r, full_name="Asha Devi", roll_number="12")
        with connection.cursor() as cur:
            cur.execute("SELECT full_name FROM rosters_student WHERE id=%s", [s.id])
            raw = cur.fetchone()[0]
        self.assertNotEqual(raw, "Asha Devi")          # stored ciphertext
        self.assertEqual(Student.objects.get(id=s.id).full_name, "Asha Devi")  # decrypts on read
```
- [ ] **Step 4 (impl):** `backend/rosters/models.py`:
```python
from django.conf import settings
from django.db import models

from common.models import OwnerScopedModel
from common.encryption import EncryptedTextField


class Roster(OwnerScopedModel):
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    class_group = models.ForeignKey("assessments.ClassGroup", null=True, blank=True, on_delete=models.SET_NULL, related_name="rosters")
    name = models.CharField(max_length=255)

    class Meta(OwnerScopedModel.Meta):
        ordering = ["name", "id"]

    def __str__(self):
        return self.name


class Student(models.Model):
    roster = models.ForeignKey(Roster, on_delete=models.CASCADE, related_name="students")
    full_name = EncryptedTextField(blank=True, default="")
    roll_number = models.CharField(max_length=32)
    external_ref = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        ordering = ["roll_number", "id"]
        constraints = [models.UniqueConstraint(fields=["roster", "roll_number"], name="uniq_roll_per_roster")]
```
Serializers: `StudentSerializer` (full_name, roll_number, external_ref); `RosterSerializer` (name, class_group [validate belongs to user], read students count). Views: `RosterViewSet(ScopedModelViewSet, owner_extra_fields=("created_by",))`; `StudentViewSet` (child-scope: `IsAuthenticated`, `get_queryset` filters `roster__user=request.user`, `?roster=` filter; `validate_roster`). Plus a roster action `add_count` (POST `{count}` → create lightweight Students numbered 1..count with roll_number=str(i), blank names). Register `rosters`, `students` in a router; include in config/urls. makemigrations + migrate.
- [ ] **Step 5:** tests green; full suite; commit `feat(rosters): Roster + Student (encrypted PII) + scoped endpoints`.

## Task 2: OMR geometry / template descriptor (TDD)
**Files:** `backend/omr/geometry.py`, `backend/omr/tests_omr.py`.
- [ ] **Step 1 (red):** test `build_template(num_questions, num_options, roll_digits)` returns a dict with: `page_px` [W,H], `dpi`, `fiducials` (4 {cx,cy}), `roll_grid` {origin,col_pitch,row_pitch,radius,cols,rows=10}, `qr` {x,y,size}, `answer_bubbles` (list per printed question position: {q_pos, page, options:[{label,cx,cy,r}]}), `page_count`, `page_map`. Assert: 4 fiducials; answer_bubbles length == num_questions; every bubble within page bounds; num_options bubbles per question; page_count = ceil(num_questions / (2*25)).
- [ ] **Step 2:** FAIL. **Step 3 (impl):** `omr/geometry.py` — a pure function computing the canonical-pixel layout per D1–D5. Constants: `DPI=100`, A4 px `W=827,H=1169`, `MARGIN=40`, `FID=24`, `ANSWER_ROWS_PER_COL=25`, bubble `R=9`, pitches sized to fit. Lay fiducial centers at the 4 corners (margin+FID/2). Place the QR top-right under the fiducial. Roll grid below the header on page 1. Answer grid: 2 columns; for question index i, page = i // 50, within-page index j = i % 50, column = j // 25, row = j % 25; compute cx/cy from column/row pitch; options laid horizontally from a per-row origin. Build `page_map` = {page: [q_pos,...]}. Return the dict. (Write the full geometry code; keep it deterministic and bounds-checked.)
- [ ] **Step 4:** green; commit `feat(omr): canonical template descriptor geometry`.

## Task 3: Deterministic shuffle + answer key (TDD)
**Files:** `backend/omr/shuffle.py`, tests.
- [ ] **Step 1 (red):** `build_sheet_plan(questions, seed, shuffle_questions, shuffle_options)` where `questions` is a list of {id, options:[{label,is_correct}]}. Returns `question_order` (list of ids), `option_order` ({id:[labels]}), `answer_key` ({printed_pos(str):[correct printed labels]}). Tests: same seed → identical output (determinism); a question's correct option(s) map correctly through the option permutation; with shuffle off, order is identity.
- [ ] **Step 2:** FAIL. **Step 3 (impl):** use `random.Random(seed)`; shuffle a copy of question ids if `shuffle_questions`; for each question, shuffle a copy of its option labels if `shuffle_options`; `answer_key[str(pos)]` = the printed labels (positions) whose underlying option `is_correct`. Return the three structures. **Step 4:** green; commit `feat(omr): deterministic per-sheet shuffle + answer key`.

## Task 4: OmrSheet model + ReportLab generator + QR round-trip (TDD — hardest)
**Files:** `backend/omr/{models.py,codes.py,generator.py}`, tests, migration.
- [ ] **Step 1:** `omr/codes.py`: `make_sheet_code(test_id, seed)` → `(sheet_code, human_code)` deterministic. `omr/models.py`: `OmrSheet` (child-scope via test) with fields: `test` FK, `student` FK null, `sheet_code` unique, `human_readable_code`, `shuffle_version` int, `question_order` JSONField, `option_order` JSONField, `answer_key` JSONField, `template_descriptor` JSONField, `page_count` int, `page_map` JSONField, `pdf_file` FileField(null), `assembly_status` default "partial". makemigrations+migrate.
- [ ] **Step 2 (red) generator tests:** `render_sheet_pdf(sheet_dict, descriptor) -> bytes` produces a valid PDF whose page count == descriptor page_count; and a **QR round-trip**: render page 1 to a PNG with PyMuPDF (`fitz.open(stream=pdf, filetype="pdf")`, `page.get_pixmap(dpi=150)`), decode with `pyzbar.decode` → the decoded string starts with the sheet_code. Also a determinism test: same inputs → identical PDF bytes (set ReportLab to not embed timestamps — pass a fixed `producer`/no info, or compare the drawn content via re-render equality of page count + QR).
```python
    def test_qr_roundtrip(self):
        import fitz
        from pyzbar.pyzbar import decode
        from PIL import Image
        import io
        pdf = render_sheet_pdf(sheet_dict, descriptor)          # sheet_dict carries sheet_code, header, roll, answer plan
        doc = fitz.open(stream=pdf, filetype="pdf")
        pix = doc[0].get_pixmap(dpi=150)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        codes = decode(img)
        self.assertTrue(any(d.data.decode().startswith(sheet_dict["sheet_code"]) for d in codes))
```
- [ ] **Step 3 (impl):** `omr/generator.py` using `reportlab.pdfgen.canvas` on A4. For each page: draw 4 fiducial squares, the QR (generate `qrcode.make(f"{code}|{page}|{total}").get_image()` → draw via `canvas.drawImage(ImageReader(...))`), header text (page 1), roll-number dot-grid bubbles (page 1) with digit labels, and the answer bubbles for that page's questions (circle outlines + option labels + question numbers), using the descriptor's px coords mapped to points. Helper `px_to_pt(x,y,H)`. Multi-page via `canvas.showPage()`. Return `canvas` buffer bytes. Make output deterministic (no timestamp: `canvas.setProducer("omrflow")`; ReportLab includes a creation date — for the determinism test, compare page_count + QR decode rather than exact bytes, OR set `canvas._doc.info` dates; simplest: assert page count + QR, not byte-equality).
- [ ] **Step 4:** green (PDF valid, QR decodes). commit `feat(omr): ReportLab sheet generator (QR/fiducials/roll-grid/answer-grid)`.

## Task 5: Generation endpoint + gates + batch PDF (TDD)
**Files:** `backend/omr/{serializers,views,urls}.py`, tests.
- [ ] **Step 1 (red):** `POST /api/v1/omr/generate/` `{test, roster, shuffle_questions, shuffle_options}` → 201 returns the created OmrSheets (one per student) + a batch pdf url. Tests: creates one sheet per student with stored question_order/answer_key/template_descriptor; deterministic sheet_codes; **gate** >10 students → 403; **gate** 6th generation in a day → 403; cross-tenant test/roster → 400.
- [ ] **Step 2:** FAIL. **Step 3 (impl):** a view that: validates test+roster belong to the user; counts students (≤10 else 403); counts today's generations for the user (a `GenerationLog` row or count OmrSheet batches — simplest: a `Generation` model with user+created_at, or count sheets created today grouped — use a small `GenerationEvent` model: user, created_at; ≤5/day) ; for each student builds the sheet plan (shuffle), descriptor (geometry from the test's question/option counts), sheet_code, renders the sheet PDF; merges all student PDFs into one batch PDF (PyMuPDF `insert_pdf` or ReportLab onto one canvas); saves each OmrSheet (+ optional per-sheet pdf) and the batch PDF to MEDIA; records a GenerationEvent. Return the sheets + batch pdf URL. Add `GET /api/v1/omr/sheets/?test=` (list) and serve the batch via MEDIA. Register routes.
- [ ] **Step 4:** green incl. both gates. Full suite. commit `feat(omr): generation endpoint with free-tier gates + batch PDF`.

## Task 6: Frontend — roster + generate sheets
**Files:** `src/api/omr.js`, `routes/Rosters.jsx`, `routes/RosterDetail.jsx`, generate UI, App routes.
- `omr.js`: listRosters/createRoster/addCount/listStudents/addStudent/generate/listSheets.
- **Rosters.jsx** (protected): list/create rosters; link to detail.
- **RosterDetail.jsx**: students table; two add modes — add named+roll student, or "count-only" (count → addCount). 
- **Generate flow** (on a test, e.g. a button on TestList → modal): pick roster + shuffle toggles → `generate` → on success show a "Download sheets PDF" link (the batch pdf URL) + toast. Handle 403 gate errors with a clear upgrade toast.
- Custom components only; build clean; commit `feat(omr): roster management + generate sheets UI`.

## Task 7: Phase 3 wrap-up + review + merge
- [ ] Full backend suite + check + frontend build green; `makemigrations --check` clean.
- [ ] Review (determinism, QR round-trip holds, gates enforced, scope/PII): the generator+scanner contract (`template_descriptor`) is stored and consistent.
- [ ] Memory updates (Phase 3 done; next Phase 4 — scanning); merge `phase-3` → `main`.

## Self-review
- Coverage: Roster/Student (encrypted) ✓(T1); descriptor geometry ✓(T2); deterministic shuffle+key
  ✓(T3); OmrSheet + ReportLab generator + QR round-trip ✓(T4); generation endpoint + gates + batch
  ✓(T5); roster+generate UI ✓(T6). The `template_descriptor` (generator↔scanner contract) is stored
  per sheet for Phase 4.
- Open/deferred: exact print DPI calibration + fiducial robustness tuned against Phase-4 fixtures;
  image questions on sheets deferred; option-count >6 unsupported (clamped).
