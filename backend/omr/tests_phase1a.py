"""
Phase 1A tests — Mode scaffold + Mode B pre-bubbled roll generation.

Coverage:
  1. build_template compat shim: standard descriptor unchanged + new roll_grid.kind/prefilled keys.
  2. build_template with roll_kind="prebubbled": roll_grid.prefilled == True.
  3. Real rendered-PDF round-trip reliability proof:
       - Generate a prebubbled sheet for roll "042".
       - Render to image via render_canonical_image (scale=2.0).
       - Run through to_binary/Otsu + read_roll.
       - Assert recovered roll == "042".
       - Assert sampled fill at each pre-bubbled cell >= FILL_HIGH + 0.2.
  4. GenerateView Mode B: roster_prebubbled test → POST generate → sheets have
     roll_kind=="prebubbled" and roll_value set → HTTP 201.
"""

import io

import numpy as np
import fitz
from django.test import TestCase

from omr.codes import make_sheet_code
from omr.geometry import build_template
from omr.generator import render_sheet_pdf
from omr.scan.read import FILL_HIGH, to_binary, bubble_fill_ratio, read_roll


# ---------------------------------------------------------------------------
# 1. Geometry — standard compat shim: additive new keys, stable values
# ---------------------------------------------------------------------------

class BuildTemplateCompatTests(TestCase):
    """Standard (default) descriptor is unchanged except for two new additive keys."""

    def _build_standard(self):
        return build_template(num_questions=50, num_options=4, roll_digits=3)

    def test_standard_descriptor_has_all_existing_keys(self):
        t = self._build_standard()
        for key in ("page_px", "dpi", "fiducials", "roll_grid", "qr",
                    "answer_bubbles", "page_count", "page_map"):
            self.assertIn(key, t, f"Missing key: {key}")

    def test_standard_page_px_unchanged(self):
        t = self._build_standard()
        self.assertEqual(t["page_px"], [827, 1169])

    def test_standard_roll_grid_has_existing_keys(self):
        t = self._build_standard()
        rg = t["roll_grid"]
        for key in ("origin", "col_pitch", "row_pitch", "radius", "cols", "rows"):
            self.assertIn(key, rg, f"roll_grid missing existing key: {key}")

    def test_standard_roll_grid_new_kind_key(self):
        """Standard descriptor now carries roll_grid.kind == "writein"."""
        t = self._build_standard()
        self.assertEqual(t["roll_grid"]["kind"], "writein")

    def test_standard_roll_grid_new_prefilled_key(self):
        """Standard descriptor now carries roll_grid.prefilled == False."""
        t = self._build_standard()
        self.assertIs(t["roll_grid"]["prefilled"], False)

    def test_standard_roll_grid_cols(self):
        t = build_template(num_questions=10, num_options=4, roll_digits=5)
        self.assertEqual(t["roll_grid"]["cols"], 5)
        self.assertEqual(t["roll_grid"]["rows"], 10)

    def test_standard_answer_bubbles_count(self):
        t = self._build_standard()
        self.assertEqual(len(t["answer_bubbles"]), 50)


# ---------------------------------------------------------------------------
# 2. Geometry — prebubbled spec
# ---------------------------------------------------------------------------

class BuildTemplatePrebubbledTests(TestCase):
    """build_template with roll_kind="prebubbled" sets roll_grid.prefilled=True."""

    def _build_prebubbled(self, roll_digits=3):
        return build_template(
            num_questions=10,
            num_options=4,
            roll_digits=roll_digits,
            roll_kind="prebubbled",
        )

    def test_prebubbled_kind_is_prebubbled(self):
        t = self._build_prebubbled()
        self.assertEqual(t["roll_grid"]["kind"], "prebubbled")

    def test_prebubbled_prefilled_is_true(self):
        t = self._build_prebubbled()
        self.assertIs(t["roll_grid"]["prefilled"], True)

    def test_prebubbled_geometry_unchanged(self):
        """Geometry values (origin, col_pitch, radius, cols, rows) are same as writein."""
        t_std = build_template(num_questions=10, num_options=4, roll_digits=3)
        t_pre = self._build_prebubbled(roll_digits=3)
        rg_std = t_std["roll_grid"]
        rg_pre = t_pre["roll_grid"]
        for key in ("origin", "col_pitch", "row_pitch", "radius", "cols", "rows"):
            self.assertEqual(rg_pre[key], rg_std[key],
                             f"roll_grid.{key} differs: prebubbled={rg_pre[key]} std={rg_std[key]}")

    def test_none_roll_kind(self):
        t = build_template(num_questions=10, num_options=4, roll_digits=3, roll_kind="none")
        self.assertEqual(t["roll_grid"]["kind"], "none")
        self.assertIs(t["roll_grid"]["prefilled"], False)


# ---------------------------------------------------------------------------
# 3. Rendered-PDF round-trip reliability proof
# ---------------------------------------------------------------------------

class PrebubbedPDFRoundTripTests(TestCase):
    """
    Key reliability test: generate a pre-bubbled PDF, rasterise it via fitz
    (same path as the production scanner), binarise with Otsu, and assert that:
      (a) read_roll recovers the correct roll string, and
      (b) the sampled fill ratio at each pre-bubbled cell is >= FILL_HIGH + 0.2.

    This proves machine-printed solid discs read reliably on the SHIPPED
    scanner path, not just via simulate.py's direct pixel-fill.
    """

    ROLL = "042"
    SCALE = 2.0  # match scanner / tests_scan.py QR-decode tests

    def _make_prebubbled_image(self, roll: str) -> tuple[np.ndarray, dict]:
        """
        Build descriptor + sheet dict, render to PDF, rasterise page 0 at
        SCALE * 100 DPI → grayscale ndarray.  Returns (img, descriptor).
        """
        roll_digits = len(roll)
        descriptor = build_template(
            num_questions=10,
            num_options=4,
            roll_digits=roll_digits,
            roll_kind="prebubbled",
        )
        sheet_code, human_code = make_sheet_code(99, 12345)
        sheet_dict = {
            "sheet_code": sheet_code,
            "human_readable_code": human_code,
            "institution": "Test Inst",
            "test_title": "Phase 1A Reliability Test",
            "subject": "",
            "student_name": "Test Student",
            "roll_label": "Roll No.",
            "roll_digits": roll_digits,
            "roll_value": roll,
        }
        pdf_bytes = render_sheet_pdf(sheet_dict, descriptor)

        # Rasterise using fitz at SCALE (same path as production scanner)
        W, H = descriptor["page_px"]
        W_out = round(W * self.SCALE)
        H_out = round(H * self.SCALE)
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        fitz_page = doc[0]
        scale_x = W_out / fitz_page.rect.width
        scale_y = H_out / fitz_page.rect.height
        mat = fitz.Matrix(scale_x, scale_y)
        pix = fitz_page.get_pixmap(matrix=mat)
        import io as _io
        from PIL import Image as PILImage
        img_pil = PILImage.open(_io.BytesIO(pix.tobytes("png"))).convert("L")
        img = np.array(img_pil, dtype=np.uint8)
        return img, descriptor

    def _scale_descriptor(self, descriptor: dict, scale: float) -> dict:
        """
        Return a copy of descriptor with all pixel coordinates scaled by `scale`,
        so that read.py (which uses descriptor coords) can sample the scaled image.
        """
        import copy
        d = copy.deepcopy(descriptor)
        rg = d["roll_grid"]
        rg["origin"] = [c * scale for c in rg["origin"]]
        rg["col_pitch"] = rg["col_pitch"] * scale
        rg["row_pitch"] = rg["row_pitch"] * scale
        rg["radius"] = rg["radius"] * scale
        # Fiducials must scale too: the reader calibrates this page's ink level
        # from them, so leaving them at canonical coordinates samples blank
        # paper and every bubble then measures against a nonsense reference.
        for f in d.get("fiducials", []):
            f["cx"] = f["cx"] * scale
            f["cy"] = f["cy"] * scale
        # Scale answer bubbles too (needed by read_answers, not used here)
        for b in d["answer_bubbles"]:
            for opt in b["options"]:
                opt["cx"] = opt["cx"] * scale
                opt["cy"] = opt["cy"] * scale
                opt["r"] = opt["r"] * scale
        return d

    def test_recovered_roll_matches_original(self):
        """
        After rendering a prebubbled PDF and Otsu-binarising it, read_roll must
        recover the correct roll string with no flag (clean read).
        """
        img, descriptor = self._make_prebubbled_image(self.ROLL)
        binary = to_binary(img)
        scaled_desc = self._scale_descriptor(descriptor, self.SCALE)

        roll_str, flag = read_roll(img, scaled_desc)

        self.assertEqual(roll_str, self.ROLL,
                         f"Expected roll {self.ROLL!r}, got {roll_str!r} (flag={flag})")
        self.assertIsNone(flag,
                          f"Expected no roll_unreadable flag, got flag={flag!r}")

    def test_prebubbled_cells_fill_well_above_threshold(self):
        """
        The sampled fill ratio at each pre-bubbled cell must be >= FILL_HIGH + 0.2
        (i.e. >= 0.65), proving a clear margin above the FILL_HIGH (0.45) threshold.
        """
        img, descriptor = self._make_prebubbled_image(self.ROLL)
        binary = to_binary(img)
        scaled_desc = self._scale_descriptor(descriptor, self.SCALE)

        rg = scaled_desc["roll_grid"]
        ox, oy = rg["origin"]
        col_pitch = rg["col_pitch"]
        row_pitch = rg["row_pitch"]
        radius = rg["radius"]

        min_fill = FILL_HIGH + 0.2  # reliability margin

        for col_idx, digit_char in enumerate(self.ROLL):
            digit = int(digit_char)
            cx = ox + col_idx * col_pitch
            cy = oy + digit * row_pitch
            ratio = bubble_fill_ratio(binary, cx, cy, radius)
            self.assertGreaterEqual(
                ratio, min_fill,
                f"Pre-bubbled cell (col={col_idx}, digit={digit}) fill ratio={ratio:.3f} "
                f"is below FILL_HIGH+0.2={min_fill:.2f}. FILL_HIGH={FILL_HIGH}."
            )

    def test_empty_cells_read_below_fill_low(self):
        """
        Non-pre-bubbled cells in the same column should be empty (outline only),
        reading below FILL_HIGH to avoid false positives.
        """
        from omr.scan.read import FILL_LOW
        img, descriptor = self._make_prebubbled_image(self.ROLL)
        binary = to_binary(img)
        scaled_desc = self._scale_descriptor(descriptor, self.SCALE)

        rg = scaled_desc["roll_grid"]
        ox, oy = rg["origin"]
        col_pitch = rg["col_pitch"]
        row_pitch = rg["row_pitch"]
        radius = rg["radius"]

        for col_idx, digit_char in enumerate(self.ROLL):
            filled_digit = int(digit_char)
            for row in range(10):
                if row == filled_digit:
                    continue  # skip the pre-filled cell
                cx = ox + col_idx * col_pitch
                cy = oy + row * row_pitch
                ratio = bubble_fill_ratio(binary, cx, cy, radius)
                # Empty outline rings may have a small ratio; must be below FILL_HIGH
                self.assertLess(
                    ratio, FILL_HIGH,
                    f"Unfilled cell (col={col_idx}, row={row}) has fill ratio={ratio:.3f} "
                    f">= FILL_HIGH={FILL_HIGH} — would be falsely detected as filled."
                )


# ---------------------------------------------------------------------------
# 4. GenerateView — Mode B end-to-end
# ---------------------------------------------------------------------------

class GenerateViewModeBTests(TestCase):
    """
    POST /api/v1/omr/generate/ with a roster_prebubbled test.
    Asserts that:
      - Response is 201.
      - Each created OmrSheet has roll_kind == "prebubbled".
      - Each created OmrSheet has roll_value == student.roll_number.
    """

    GENERATE_URL = "/api/v1/omr/generate/"

    def setUp(self):
        from django.contrib.auth import get_user_model
        from assessments.models import ClassGroup, Option, Question, Test
        from rosters.models import Roster, Student

        User = get_user_model()
        self.user = User.objects.create_user(email="modeb@example.com", password="pass")

        cg = ClassGroup.objects.create(user=self.user, created_by=self.user, name="CG-ModeB")
        self.test = Test.objects.create(
            user=self.user,
            class_group=cg,
            created_by=self.user,
            title="Mode B Test",
            mode="roster_prebubbled",
        )

        # Add questions with options
        for qi in range(3):
            q = Question.objects.create(test=self.test, order_index=qi, text=f"Q{qi}")
            for label in ["A", "B", "C", "D"]:
                Option.objects.create(question=q, label=label, text=label,
                                      is_correct=(label == "A"))

        # Roster with 3 students with distinct roll numbers
        self.roster = Roster.objects.create(
            user=self.user, created_by=self.user, name="Roster-ModeB"
        )
        self.students = []
        for i in range(1, 4):
            s = Student.objects.create(
                roster=self.roster, roll_number=str(10 + i), full_name=f"Student {i}"
            )
            self.students.append(s)

    def _auth(self):
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(self.user)
        return {"HTTP_AUTHORIZATION": f"Bearer {str(refresh.access_token)}"}

    def test_generate_mode_b_returns_201(self):
        resp = self.client.post(
            self.GENERATE_URL,
            {"test": self.test.id, "roster": self.roster.id},
            content_type="application/json",
            **self._auth(),
        )
        self.assertEqual(resp.status_code, 201, resp.content)

    def test_generate_mode_b_sheets_have_roll_kind_prebubbled(self):
        from omr.models import OmrSheet

        resp = self.client.post(
            self.GENERATE_URL,
            {"test": self.test.id, "roster": self.roster.id},
            content_type="application/json",
            **self._auth(),
        )
        self.assertEqual(resp.status_code, 201, resp.content)

        sheets = OmrSheet.objects.filter(test=self.test)
        self.assertEqual(sheets.count(), len(self.students))
        for sheet in sheets:
            self.assertEqual(
                sheet.roll_kind, "prebubbled",
                f"Sheet {sheet.sheet_code} has roll_kind={sheet.roll_kind!r}, expected 'prebubbled'"
            )

    def test_generate_mode_b_sheets_have_correct_roll_value(self):
        from omr.models import OmrSheet

        resp = self.client.post(
            self.GENERATE_URL,
            {"test": self.test.id, "roster": self.roster.id},
            content_type="application/json",
            **self._auth(),
        )
        self.assertEqual(resp.status_code, 201, resp.content)

        for student in self.students:
            sheet = OmrSheet.objects.get(test=self.test, student=student)
            self.assertEqual(
                sheet.roll_value, student.roll_number,
                f"Sheet for student {student.roll_number} has roll_value={sheet.roll_value!r}"
            )

    def test_generate_mode_b_descriptor_has_prefilled_true(self):
        """The stored template_descriptor for Mode B sheets has roll_grid.prefilled=True."""
        from omr.models import OmrSheet

        resp = self.client.post(
            self.GENERATE_URL,
            {"test": self.test.id, "roster": self.roster.id},
            content_type="application/json",
            **self._auth(),
        )
        self.assertEqual(resp.status_code, 201, resp.content)

        sheets = OmrSheet.objects.filter(test=self.test)
        for sheet in sheets:
            rg = sheet.template_descriptor.get("roll_grid", {})
            self.assertIs(rg.get("prefilled"), True,
                          f"template_descriptor.roll_grid.prefilled != True for {sheet.sheet_code}")
            self.assertEqual(rg.get("kind"), "prebubbled")

    def test_generate_standard_mode_has_writein_roll_kind(self):
        """A standard-mode test still produces sheets with roll_kind='writein'."""
        from assessments.models import ClassGroup, Option, Question, Test
        from rosters.models import Roster, Student
        from omr.models import OmrSheet

        # Create a standard-mode test
        cg = self.test.class_group
        std_test = Test.objects.create(
            user=self.user, class_group=cg, created_by=self.user,
            title="Standard Test", mode="standard"
        )
        for qi in range(3):
            q = Question.objects.create(test=std_test, order_index=qi, text=f"QS{qi}")
            for label in ["A", "B", "C", "D"]:
                Option.objects.create(question=q, label=label, text=label,
                                      is_correct=(label == "A"))

        resp = self.client.post(
            self.GENERATE_URL,
            {"test": std_test.id, "roster": self.roster.id},
            content_type="application/json",
            **self._auth(),
        )
        self.assertEqual(resp.status_code, 201, resp.content)

        sheets = OmrSheet.objects.filter(test=std_test)
        for sheet in sheets:
            self.assertEqual(sheet.roll_kind, "writein")
            self.assertEqual(sheet.roll_value, "")

    def test_generate_mode_b_idempotent(self):
        """Re-generating a Mode B test is idempotent — same pks, same roll_kind."""
        from omr.models import OmrSheet

        payload = {"test": self.test.id, "roster": self.roster.id}

        first = self.client.post(
            self.GENERATE_URL, payload, content_type="application/json", **self._auth()
        )
        self.assertEqual(first.status_code, 201, first.content)
        pks_first = set(OmrSheet.objects.filter(test=self.test).values_list("pk", flat=True))

        second = self.client.post(
            self.GENERATE_URL, payload, content_type="application/json", **self._auth()
        )
        self.assertEqual(second.status_code, 201, second.content)
        pks_second = set(OmrSheet.objects.filter(test=self.test).values_list("pk", flat=True))

        self.assertEqual(pks_first, pks_second, "Re-generation must reuse OmrSheet rows")
        sheets = OmrSheet.objects.filter(test=self.test)
        for sheet in sheets:
            self.assertEqual(sheet.roll_kind, "prebubbled")
