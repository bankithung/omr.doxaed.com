"""
Tests for omr.geometry and omr.shuffle — TDD, Tasks 2 & 3.
"""
import math
from django.test import TestCase


# ---------------------------------------------------------------------------
# Task 2: geometry.build_template
# ---------------------------------------------------------------------------

class GeometryBuildTemplateTests(TestCase):
    """Tests for build_template(num_questions, num_options, roll_digits)."""

    def _build(self, num_questions=100, num_options=4, roll_digits=3):
        from omr.geometry import build_template
        return build_template(num_questions, num_options, roll_digits)

    # -- structural keys --

    def test_returns_dict_with_required_keys(self):
        t = self._build()
        for key in ("page_px", "dpi", "fiducials", "roll_grid", "qr",
                    "answer_bubbles", "page_count", "page_map"):
            self.assertIn(key, t, f"Missing key: {key}")

    def test_page_px_and_dpi(self):
        t = self._build()
        self.assertEqual(t["page_px"], [827, 1169])
        self.assertEqual(t["dpi"], 100)

    # -- fiducials --

    def test_exactly_4_fiducials(self):
        t = self._build()
        self.assertEqual(len(t["fiducials"]), 4)

    def test_fiducials_have_cx_cy(self):
        t = self._build()
        for f in t["fiducials"]:
            self.assertIn("cx", f)
            self.assertIn("cy", f)

    def test_fiducials_within_page_bounds(self):
        t = self._build()
        W, H = t["page_px"]
        for f in t["fiducials"]:
            self.assertGreaterEqual(f["cx"], 0)
            self.assertLessEqual(f["cx"], W)
            self.assertGreaterEqual(f["cy"], 0)
            self.assertLessEqual(f["cy"], H)

    # -- roll_grid --

    def test_roll_grid_keys(self):
        t = self._build(roll_digits=4)
        rg = t["roll_grid"]
        for key in ("origin", "col_pitch", "row_pitch", "radius", "cols", "rows"):
            self.assertIn(key, rg, f"roll_grid missing key: {key}")

    def test_roll_grid_cols_equals_roll_digits(self):
        t = self._build(roll_digits=4)
        self.assertEqual(t["roll_grid"]["cols"], 4)

    def test_roll_grid_rows_equals_10(self):
        t = self._build()
        self.assertEqual(t["roll_grid"]["rows"], 10)

    def test_roll_grid_bubbles_within_page_bounds(self):
        t = self._build(roll_digits=3)
        W, H = t["page_px"]
        rg = t["roll_grid"]
        ox, oy = rg["origin"]
        r = rg["radius"]
        for col in range(rg["cols"]):
            for row in range(rg["rows"]):
                cx = ox + col * rg["col_pitch"]
                cy = oy + row * rg["row_pitch"]
                self.assertGreaterEqual(cx - r, 0, f"roll grid bubble left OOB col={col} row={row}")
                self.assertLessEqual(cx + r, W, f"roll grid bubble right OOB col={col} row={row}")
                self.assertGreaterEqual(cy - r, 0, f"roll grid bubble top OOB col={col} row={row}")
                self.assertLessEqual(cy + r, H, f"roll grid bubble bottom OOB col={col} row={row}")

    # -- qr --

    def test_qr_keys(self):
        t = self._build()
        for key in ("x", "y", "size"):
            self.assertIn(key, t["qr"], f"qr missing key: {key}")

    def test_qr_within_page_bounds(self):
        t = self._build()
        W, H = t["page_px"]
        q = t["qr"]
        self.assertGreaterEqual(q["x"], 0)
        self.assertGreaterEqual(q["y"], 0)
        self.assertLessEqual(q["x"] + q["size"], W)
        self.assertLessEqual(q["y"] + q["size"], H)

    # -- answer_bubbles --

    def test_answer_bubbles_length_equals_num_questions(self):
        for nq in (1, 25, 50, 100, 200):
            t = self._build(num_questions=nq)
            self.assertEqual(len(t["answer_bubbles"]), nq,
                             f"Expected {nq} bubbles, got {len(t['answer_bubbles'])}")

    def test_answer_bubbles_have_required_keys(self):
        t = self._build(num_questions=10)
        for b in t["answer_bubbles"]:
            self.assertIn("q_pos", b)
            self.assertIn("page", b)
            self.assertIn("options", b)

    def test_answer_bubbles_each_have_num_options_options(self):
        for num_opts in (2, 4, 6):
            t = self._build(num_questions=10, num_options=num_opts)
            for b in t["answer_bubbles"]:
                self.assertEqual(len(b["options"]), num_opts,
                                 f"Expected {num_opts} options per question, got {len(b['options'])}")

    def test_option_bubbles_have_label_cx_cy_r(self):
        t = self._build(num_questions=5, num_options=4)
        for b in t["answer_bubbles"]:
            for opt in b["options"]:
                for k in ("label", "cx", "cy", "r"):
                    self.assertIn(k, opt, f"option missing key: {k}")

    def test_option_bubbles_within_page_bounds(self):
        t = self._build(num_questions=200, num_options=4)
        W, H = t["page_px"]
        for b in t["answer_bubbles"]:
            for opt in b["options"]:
                self.assertGreaterEqual(opt["cx"] - opt["r"], 0,
                    f"bubble left OOB: q_pos={b['q_pos']}, label={opt['label']}")
                self.assertLessEqual(opt["cx"] + opt["r"], W,
                    f"bubble right OOB: q_pos={b['q_pos']}, label={opt['label']}")
                self.assertGreaterEqual(opt["cy"] - opt["r"], 0,
                    f"bubble top OOB: q_pos={b['q_pos']}, label={opt['label']}")
                self.assertLessEqual(opt["cy"] + opt["r"], H,
                    f"bubble bottom OOB: q_pos={b['q_pos']}, label={opt['label']}")

    # -- page_count --

    def test_page_count_formula(self):
        # page_count = ceil(num_questions / 50)
        cases = [
            (1,   1),
            (50,  1),
            (51,  2),
            (100, 2),
            (101, 3),
            (200, 4),
        ]
        for nq, expected_pages in cases:
            t = self._build(num_questions=nq)
            self.assertEqual(t["page_count"], expected_pages,
                             f"num_questions={nq}: expected page_count={expected_pages}")

    def test_page_map_covers_all_questions(self):
        nq = 75
        t = self._build(num_questions=nq)
        all_positions = []
        for positions in t["page_map"].values():
            all_positions.extend(positions)
        self.assertEqual(sorted(all_positions), list(range(nq)))

    def test_page_map_has_correct_page_keys(self):
        t = self._build(num_questions=100)
        # pages 0 and 1
        self.assertIn(0, t["page_map"])
        self.assertIn(1, t["page_map"])

    def test_answer_bubbles_q_pos_sequential(self):
        nq = 10
        t = self._build(num_questions=nq)
        q_positions = [b["q_pos"] for b in t["answer_bubbles"]]
        self.assertEqual(q_positions, list(range(nq)))

    def test_option_labels_are_letters(self):
        t = self._build(num_questions=1, num_options=4)
        labels = [opt["label"] for opt in t["answer_bubbles"][0]["options"]]
        self.assertEqual(labels, ["A", "B", "C", "D"])

    def test_single_question_single_option(self):
        t = self._build(num_questions=1, num_options=2)
        self.assertEqual(len(t["answer_bubbles"]), 1)
        self.assertEqual(len(t["answer_bubbles"][0]["options"]), 2)
        self.assertEqual(t["page_count"], 1)


# ---------------------------------------------------------------------------
# Task 3: shuffle.build_sheet_plan
# ---------------------------------------------------------------------------

class ShuffleBuildSheetPlanTests(TestCase):
    """Tests for build_sheet_plan(questions, seed, shuffle_questions, shuffle_options)."""

    def _make_questions(self, n=5, num_options=4):
        """Create n questions with options A-D; option B is always correct."""
        labels = [chr(ord("A") + i) for i in range(num_options)]
        questions = []
        for i in range(n):
            options = [
                {"label": lbl, "is_correct": (lbl == "B")}
                for lbl in labels
            ]
            questions.append({"id": i + 1, "options": options})
        return questions

    def _plan(self, questions=None, seed=42, shuffle_questions=True, shuffle_options=True):
        from omr.shuffle import build_sheet_plan
        if questions is None:
            questions = self._make_questions()
        return build_sheet_plan(questions, seed, shuffle_questions, shuffle_options)

    # -- determinism --

    def test_same_seed_same_output(self):
        questions = self._make_questions(10)
        p1 = self._plan(questions=questions, seed=99)
        p2 = self._plan(questions=questions, seed=99)
        self.assertEqual(p1["question_order"], p2["question_order"])
        self.assertEqual(p1["option_order"], p2["option_order"])
        self.assertEqual(p1["answer_key"], p2["answer_key"])

    def test_different_seeds_likely_different_order(self):
        questions = self._make_questions(10)
        p1 = self._plan(questions=questions, seed=1)
        p2 = self._plan(questions=questions, seed=2)
        # With 10 questions and different seeds, orders should differ
        # (astronomically unlikely to be the same)
        self.assertNotEqual(p1["question_order"], p2["question_order"])

    # -- return structure --

    def test_returns_required_keys(self):
        p = self._plan()
        for key in ("question_order", "option_order", "answer_key"):
            self.assertIn(key, p, f"Missing key: {key}")

    def test_question_order_length(self):
        questions = self._make_questions(7)
        p = self._plan(questions=questions)
        self.assertEqual(len(p["question_order"]), 7)

    def test_question_order_is_permutation_of_ids(self):
        questions = self._make_questions(5)
        p = self._plan(questions=questions)
        self.assertEqual(sorted(p["question_order"]), [q["id"] for q in questions])

    def test_option_order_has_entry_per_question(self):
        questions = self._make_questions(5)
        p = self._plan(questions=questions)
        for q in questions:
            key = str(q["id"]) if str(q["id"]) in p["option_order"] else q["id"]
            self.assertIn(key, p["option_order"],
                          f"option_order missing question id {q['id']}")

    def test_option_order_is_permutation_of_labels(self):
        questions = self._make_questions(5, num_options=4)
        p = self._plan(questions=questions)
        for q in questions:
            qid = q["id"]
            key = str(qid) if str(qid) in p["option_order"] else qid
            printed_labels = p["option_order"][key]
            original_labels = [o["label"] for o in q["options"]]
            self.assertEqual(sorted(printed_labels), sorted(original_labels))

    # -- answer_key correctness --

    def test_answer_key_maps_correct_option_through_shuffle(self):
        """
        For each question, option B is correct. After shuffling, the answer_key
        for the printed position must point to the printed label that B was
        remapped to.
        """
        questions = self._make_questions(5, num_options=4)
        p = self._plan(questions=questions, seed=42)

        for printed_pos, q_id in enumerate(p["question_order"]):
            key = str(q_id) if str(q_id) in p["option_order"] else q_id
            printed_labels = p["option_order"][key]
            # original label B is correct; it was placed at position printed_labels.index("B")
            # which corresponds to the letter chr(ord("A") + idx)
            original_correct = "B"
            # Find where "B" landed in printed order — it became label at that index
            b_idx = printed_labels.index(original_correct)
            expected_printed_correct = chr(ord("A") + b_idx)

            pos_key = str(printed_pos)
            self.assertIn(pos_key, p["answer_key"],
                          f"answer_key missing printed_pos {pos_key}")
            self.assertIn(expected_printed_correct, p["answer_key"][pos_key],
                          f"Printed pos {pos_key}: expected {expected_printed_correct} in answer_key, "
                          f"got {p['answer_key'][pos_key]}")

    def test_answer_key_keys_are_printed_positions_as_strings(self):
        questions = self._make_questions(5)
        p = self._plan(questions=questions)
        # keys should be str(0), str(1), ... str(n-1)
        expected_keys = {str(i) for i in range(len(questions))}
        self.assertEqual(set(p["answer_key"].keys()), expected_keys)

    # -- identity (no shuffle) --

    def test_no_shuffle_questions_preserves_order(self):
        questions = self._make_questions(5)
        p = self._plan(questions=questions, shuffle_questions=False, shuffle_options=False)
        self.assertEqual(p["question_order"], [q["id"] for q in questions])

    def test_no_shuffle_options_preserves_labels(self):
        questions = self._make_questions(5, num_options=4)
        p = self._plan(questions=questions, shuffle_questions=False, shuffle_options=False)
        for q in questions:
            qid = q["id"]
            key = str(qid) if str(qid) in p["option_order"] else qid
            original_labels = [o["label"] for o in q["options"]]
            self.assertEqual(p["option_order"][key], original_labels)

    def test_no_shuffle_answer_key_references_original_labels(self):
        """With no shuffle, correct option B stays as printed option B."""
        questions = self._make_questions(5, num_options=4)
        p = self._plan(questions=questions, shuffle_questions=False, shuffle_options=False)
        for pos_str, correct_labels in p["answer_key"].items():
            self.assertEqual(correct_labels, ["B"])

    # -- multiple correct options --

    def test_multiple_correct_options_all_tracked(self):
        """Question with 2 correct options; both must appear in answer_key."""
        questions = [
            {"id": 1, "options": [
                {"label": "A", "is_correct": True},
                {"label": "B", "is_correct": False},
                {"label": "C", "is_correct": True},
                {"label": "D", "is_correct": False},
            ]}
        ]
        p = self._plan(questions=questions, seed=7)
        key = str(1) if str(1) in p["option_order"] else 1
        printed_labels = p["option_order"][key]
        # Correct originals: A and C
        correct_originals = {"A", "C"}
        # Find printed positions of A and C
        expected_printed = set()
        for orig in correct_originals:
            idx = printed_labels.index(orig)
            expected_printed.add(chr(ord("A") + idx))

        pos_str = str(0)  # first (and only) printed position
        self.assertEqual(set(p["answer_key"][pos_str]), expected_printed)


# ---------------------------------------------------------------------------
# Task 4: OmrSheet model + codes.py + generator.py
# ---------------------------------------------------------------------------

class OmrSheetModelTests(TestCase):
    """OmrSheet model: save and round-trip JSON fields."""

    def _make_test(self, email="t4@example.com"):
        from django.contrib.auth import get_user_model
        from assessments.models import ClassGroup, Test
        User = get_user_model()
        user = User.objects.create_user(email=email, password="pass")
        cg = ClassGroup.objects.create(user=user, created_by=user, name="CG4")
        return Test.objects.create(user=user, class_group=cg, created_by=user, title="T4")

    def test_omrsheet_save_and_reload(self):
        from omr.models import OmrSheet
        from omr.codes import make_sheet_code

        test = self._make_test()
        sheet_code, human_code = make_sheet_code(test.id, seed=1)

        sheet = OmrSheet.objects.create(
            test=test,
            sheet_code=sheet_code,
            human_readable_code=human_code,
            shuffle_version=1,
            question_order=[1, 2, 3],
            option_order={"1": ["A", "B"], "2": ["B", "A"], "3": ["A", "B"]},
            answer_key={"0": ["A"], "1": ["B"], "2": ["A"]},
            template_descriptor={"page_px": [827, 1169], "page_count": 1},
            page_count=1,
            page_map={"0": [0, 1, 2]},
        )

        reloaded = OmrSheet.objects.get(pk=sheet.pk)
        self.assertEqual(reloaded.sheet_code, sheet_code)
        self.assertEqual(reloaded.human_readable_code, human_code)
        self.assertEqual(reloaded.question_order, [1, 2, 3])
        self.assertEqual(reloaded.option_order, {"1": ["A", "B"], "2": ["B", "A"], "3": ["A", "B"]})
        self.assertEqual(reloaded.answer_key, {"0": ["A"], "1": ["B"], "2": ["A"]})
        self.assertEqual(reloaded.page_count, 1)

    def test_sheet_code_unique(self):
        from omr.models import OmrSheet
        from omr.codes import make_sheet_code
        from django.db import IntegrityError

        test = self._make_test(email="t4b@example.com")
        sheet_code, human_code = make_sheet_code(test.id, seed=999)

        OmrSheet.objects.create(
            test=test,
            sheet_code=sheet_code,
            human_readable_code=human_code,
            page_count=1,
        )
        with self.assertRaises(IntegrityError):
            OmrSheet.objects.create(
                test=test,
                sheet_code=sheet_code,
                human_readable_code=human_code,
                page_count=1,
            )


class SheetCodesTests(TestCase):
    """omr.codes.make_sheet_code — determinism + format."""

    def test_deterministic(self):
        from omr.codes import make_sheet_code
        c1, h1 = make_sheet_code(42, 100)
        c2, h2 = make_sheet_code(42, 100)
        self.assertEqual(c1, c2)
        self.assertEqual(h1, h2)

    def test_different_seeds_different_codes(self):
        from omr.codes import make_sheet_code
        c1, _ = make_sheet_code(42, 1)
        c2, _ = make_sheet_code(42, 2)
        self.assertNotEqual(c1, c2)

    def test_different_test_ids_different_codes(self):
        from omr.codes import make_sheet_code
        c1, _ = make_sheet_code(1, 42)
        c2, _ = make_sheet_code(2, 42)
        self.assertNotEqual(c1, c2)

    def test_format(self):
        import uuid as _uuid
        from omr.codes import make_sheet_code
        from omr.scan.pipeline import _test_id_prefix

        test_id = _uuid.uuid4()
        code, human = make_sheet_code(test_id, 42)
        # sheet_code is "{first 8 hex of the test UUID}-XXXXXXXX"
        self.assertTrue(
            code.startswith(f"{_test_id_prefix(test_id)}-"), f"Bad prefix: {code}"
        )
        token = code.split("-")[1]
        self.assertEqual(len(token), 8)
        self.assertEqual(token, human)
        # base32 chars: A-Z and 2-7
        import re
        self.assertRegex(token, r'^[A-Z2-7]{8}$')


class GeneratorTests(TestCase):
    """
    omr.generator.render_sheet_pdf — PDF validity, QR round-trip, determinism.
    """

    def _make_descriptor(self, num_questions=60):
        from omr.geometry import build_template
        return build_template(num_questions=num_questions, num_options=4, roll_digits=3)

    def _make_sheet_dict(self, sheet_code="000001-ABCDEFGH", human_code="ABCDEFGH"):
        return {
            "sheet_code": sheet_code,
            "human_readable_code": human_code,
            "institution": "Test School",
            "test_title": "Mathematics Exam",
            "subject": "Math",
            "student_name": "Alice",
            "roll_label": "Roll No.",
            "roll_digits": 3,
        }

    def test_returns_bytes(self):
        from omr.generator import render_sheet_pdf
        descriptor = self._make_descriptor(num_questions=10)
        sheet = self._make_sheet_dict()
        pdf = render_sheet_pdf(sheet, descriptor)
        self.assertIsInstance(pdf, bytes)
        # PDF magic bytes
        self.assertTrue(pdf.startswith(b"%PDF"), f"Not a PDF: {pdf[:10]}")

    def test_page_count_matches_descriptor(self):
        """60 questions → 2 pages (50/page)."""
        import fitz
        from omr.generator import render_sheet_pdf
        descriptor = self._make_descriptor(num_questions=60)
        sheet = self._make_sheet_dict()
        pdf = render_sheet_pdf(sheet, descriptor)
        doc = fitz.open(stream=pdf, filetype="pdf")
        self.assertEqual(doc.page_count, descriptor["page_count"])
        self.assertEqual(descriptor["page_count"], 2)

    def test_qr_roundtrip(self):
        """
        Render a sheet, rasterise page 1 at 150 DPI, decode QR.
        The decoded payload must start with the sheet_code.
        """
        import io
        import fitz
        from PIL import Image
        from pyzbar.pyzbar import decode as pyzbar_decode
        from omr.generator import render_sheet_pdf

        sheet_code = "000042-TESTQRCO"
        descriptor = self._make_descriptor(num_questions=60)
        sheet = self._make_sheet_dict(sheet_code=sheet_code, human_code="TESTQRCO")

        pdf = render_sheet_pdf(sheet, descriptor)
        doc = fitz.open(stream=pdf, filetype="pdf")

        pix = doc[0].get_pixmap(dpi=150)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        codes = pyzbar_decode(img)

        self.assertTrue(
            any(d.data.decode().startswith(sheet_code) for d in codes),
            f"QR round-trip failed. Decoded: {[d.data.decode() for d in codes]}",
        )

    def test_qr_payload_format(self):
        """QR payload = sheet_code|page|total (1-indexed)."""
        import io
        import fitz
        from PIL import Image
        from pyzbar.pyzbar import decode as pyzbar_decode
        from omr.generator import render_sheet_pdf

        sheet_code = "000001-PAYLOADX"
        num_q = 60
        descriptor = self._make_descriptor(num_questions=num_q)
        sheet = self._make_sheet_dict(sheet_code=sheet_code, human_code="PAYLOADX")

        pdf = render_sheet_pdf(sheet, descriptor)
        doc = fitz.open(stream=pdf, filetype="pdf")
        total_pages = descriptor["page_count"]

        for page_no in range(total_pages):
            pix = doc[page_no].get_pixmap(dpi=150)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            codes = pyzbar_decode(img)
            found = [d.data.decode() for d in codes]
            expected_payload = f"{sheet_code}|{page_no + 1}|{total_pages}"
            self.assertTrue(
                any(d == expected_payload for d in found),
                f"Page {page_no + 1}: expected '{expected_payload}', got {found}",
            )

    def test_determinism_page_count_and_qr(self):
        """
        Rendering twice with same inputs yields same page_count and a decodable QR
        each time. (We do NOT assert byte-equality because ReportLab embeds a timestamp.)
        """
        import io
        import fitz
        from PIL import Image
        from pyzbar.pyzbar import decode as pyzbar_decode
        from omr.generator import render_sheet_pdf

        sheet_code = "000007-DETERMIN"
        descriptor = self._make_descriptor(num_questions=60)
        sheet = self._make_sheet_dict(sheet_code=sheet_code, human_code="DETERMIN")

        pdf1 = render_sheet_pdf(sheet, descriptor)
        pdf2 = render_sheet_pdf(sheet, descriptor)

        doc1 = fitz.open(stream=pdf1, filetype="pdf")
        doc2 = fitz.open(stream=pdf2, filetype="pdf")

        self.assertEqual(doc1.page_count, doc2.page_count)
        self.assertEqual(doc1.page_count, descriptor["page_count"])

        def has_qr(pdf_bytes):
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            pix = doc[0].get_pixmap(dpi=150)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            codes = pyzbar_decode(img)
            return any(d.data.decode().startswith(sheet_code) for d in codes)

        self.assertTrue(has_qr(pdf1), "First render: QR not decodable")
        self.assertTrue(has_qr(pdf2), "Second render: QR not decodable")


# ---------------------------------------------------------------------------
# Task 5: Generation endpoint + gates + batch PDF
# ---------------------------------------------------------------------------

class GenerateEndpointTests(TestCase):
    """
    POST /api/v1/omr/generate/
    GET  /api/v1/omr/sheets/?test=
    """

    GENERATE_URL = "/api/v1/omr/generate/"
    SHEETS_URL = "/api/v1/omr/sheets/"

    def setUp(self):
        from django.contrib.auth import get_user_model
        from assessments.models import ClassGroup, Option, Question, Test
        from rosters.models import Roster, Student

        User = get_user_model()

        # Primary user
        self.user = User.objects.create_user(email="gen@example.com", password="pass")
        # Second user for cross-tenant checks
        self.other_user = User.objects.create_user(email="other@example.com", password="pass")

        # Set up assessment data for self.user
        cg = ClassGroup.objects.create(user=self.user, created_by=self.user, name="CG-Gen")
        self.test = Test.objects.create(
            user=self.user, class_group=cg, created_by=self.user, title="Gen Test"
        )
        # Add 3 questions with 4 options each (option A is correct)
        for qi in range(3):
            q = Question.objects.create(test=self.test, order_index=qi, text=f"Q{qi}")
            for li, label in enumerate(["A", "B", "C", "D"]):
                Option.objects.create(
                    question=q, label=label, text=label, is_correct=(label == "A")
                )

        # Roster with 3 students
        self.roster = Roster.objects.create(
            user=self.user, created_by=self.user, name="Roster-Gen"
        )
        for i in range(1, 4):
            Student.objects.create(roster=self.roster, roll_number=str(i), full_name=f"Student {i}")

        # Cross-tenant: other user's test and roster
        cg2 = ClassGroup.objects.create(user=self.other_user, created_by=self.other_user, name="CG-Other")
        self.other_test = Test.objects.create(
            user=self.other_user, class_group=cg2, created_by=self.other_user, title="Other Test"
        )
        q2 = Question.objects.create(test=self.other_test, order_index=0, text="Q-other")
        Option.objects.create(question=q2, label="A", text="A", is_correct=True)
        Option.objects.create(question=q2, label="B", text="B", is_correct=False)

        self.other_roster = Roster.objects.create(
            user=self.other_user, created_by=self.other_user, name="Roster-Other"
        )
        for i in range(1, 4):
            Student.objects.create(roster=self.other_roster, roll_number=str(i))

    def _auth(self, user=None):
        """Return Authorization header dict, bypassing throttle via forced JWT."""
        from rest_framework_simplejwt.tokens import RefreshToken
        if user is None:
            user = self.user
        refresh = RefreshToken.for_user(user)
        return {"HTTP_AUTHORIZATION": f"Bearer {str(refresh.access_token)}"}

    # ---- happy path -------------------------------------------------------

    def test_generate_returns_201(self):
        resp = self.client.post(
            self.GENERATE_URL,
            {"test": self.test.id, "roster": self.roster.id},
            content_type="application/json",
            **self._auth(),
        )
        self.assertEqual(resp.status_code, 201, resp.content)

    def test_generate_one_sheet_per_student(self):
        from rosters.models import Student
        student_count = Student.objects.filter(roster=self.roster).count()
        resp = self.client.post(
            self.GENERATE_URL,
            {"test": self.test.id, "roster": self.roster.id},
            content_type="application/json",
            **self._auth(),
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        data = resp.json()
        self.assertEqual(data["count"], student_count)
        self.assertEqual(len(data["sheets"]), student_count)

    def test_generate_sheets_have_stored_fields(self):
        """Each OmrSheet must have question_order, answer_key, template_descriptor stored."""
        from omr.models import OmrSheet
        resp = self.client.post(
            self.GENERATE_URL,
            {"test": self.test.id, "roster": self.roster.id},
            content_type="application/json",
            **self._auth(),
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        # Verify DB rows
        sheets = OmrSheet.objects.filter(test=self.test)
        self.assertGreater(sheets.count(), 0)
        for sheet in sheets:
            self.assertIsInstance(sheet.question_order, list)
            self.assertGreater(len(sheet.question_order), 0)
            self.assertIsInstance(sheet.answer_key, dict)
            self.assertGreater(len(sheet.answer_key), 0)
            self.assertIsInstance(sheet.template_descriptor, dict)
            self.assertIn("page_px", sheet.template_descriptor)

    def test_generate_unique_sheet_codes(self):
        """Each sheet must have a distinct sheet_code."""
        resp = self.client.post(
            self.GENERATE_URL,
            {"test": self.test.id, "roster": self.roster.id},
            content_type="application/json",
            **self._auth(),
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        data = resp.json()
        codes = [s["sheet_code"] for s in data["sheets"]]
        self.assertEqual(len(codes), len(set(codes)), "Sheet codes are not unique")

    def test_regenerate_is_idempotent(self):
        """Re-generating a test's sheets must NOT 500 on the unique sheet_code
        constraint (regression). It updates rows in place: stable count, the
        same pks reused (so results stay valid), and identical codes (the seed
        is deterministic per test+student)."""
        from omr.models import OmrSheet
        from rosters.models import Student

        n_students = Student.objects.filter(roster=self.roster).count()
        payload = {"test": self.test.id, "roster": self.roster.id}

        first = self.client.post(
            self.GENERATE_URL, payload, content_type="application/json", **self._auth()
        )
        self.assertEqual(first.status_code, 201, first.content)
        self.assertEqual(OmrSheet.objects.filter(test=self.test).count(), n_students)
        pks_first = set(OmrSheet.objects.filter(test=self.test).values_list("pk", flat=True))
        codes_first = sorted(s["sheet_code"] for s in first.json()["sheets"])

        # Second generation for the SAME test+roster must succeed.
        second = self.client.post(
            self.GENERATE_URL, payload, content_type="application/json", **self._auth()
        )
        self.assertEqual(second.status_code, 201, second.content)
        self.assertEqual(
            OmrSheet.objects.filter(test=self.test).count(), n_students,
            "Re-generation must not create duplicate sheets",
        )
        pks_second = set(OmrSheet.objects.filter(test=self.test).values_list("pk", flat=True))
        self.assertEqual(pks_first, pks_second, "Re-generation must reuse rows (preserve pks)")
        self.assertEqual(
            codes_first, sorted(s["sheet_code"] for s in second.json()["sheets"])
        )

    def test_generate_batch_pdf_url_present(self):
        resp = self.client.post(
            self.GENERATE_URL,
            {"test": self.test.id, "roster": self.roster.id},
            content_type="application/json",
            **self._auth(),
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        data = resp.json()
        self.assertIn("batch_pdf_url", data)
        self.assertTrue(data["batch_pdf_url"], "batch_pdf_url must not be empty")

    def test_generate_deterministic_sheet_codes(self):
        """Same test+student pair must produce the same sheet_code on a second generation."""
        from omr.models import OmrSheet

        resp1 = self.client.post(
            self.GENERATE_URL,
            {"test": self.test.id, "roster": self.roster.id},
            content_type="application/json",
            **self._auth(),
        )
        self.assertEqual(resp1.status_code, 201, resp1.content)

        # Wipe the sheets so we can regenerate (codes are unique; second call would
        # hit the unique constraint if we reuse them, so clear first)
        OmrSheet.objects.filter(test=self.test).delete()

        resp2 = self.client.post(
            self.GENERATE_URL,
            {"test": self.test.id, "roster": self.roster.id},
            content_type="application/json",
            **self._auth(),
        )
        self.assertEqual(resp2.status_code, 201, resp2.content)

        codes1 = sorted(s["sheet_code"] for s in resp1.json()["sheets"])
        codes2 = sorted(s["sheet_code"] for s in resp2.json()["sheets"])
        self.assertEqual(codes1, codes2, "Sheet codes are not deterministic across calls")

    # ---- gate: roster size -----------------------------------------------

    def test_gate_roster_too_large_returns_403(self):
        """Roster with 11 students → 403."""
        from rosters.models import Roster, Student
        big_roster = Roster.objects.create(
            user=self.user, created_by=self.user, name="BigRoster"
        )
        for i in range(1, 12):  # 11 students
            Student.objects.create(roster=big_roster, roll_number=str(i))

        resp = self.client.post(
            self.GENERATE_URL,
            {"test": self.test.id, "roster": big_roster.id},
            content_type="application/json",
            **self._auth(),
        )
        self.assertEqual(resp.status_code, 403, resp.content)

    # ---- gate: daily generation limit ------------------------------------

    def test_gate_6th_generation_returns_403(self):
        """6th generation in a day → 403."""
        from django.utils import timezone
        from omr.models import GenerationEvent

        # Create 5 existing events for today
        for _ in range(5):
            GenerationEvent.objects.create(user=self.user, test=self.test)

        resp = self.client.post(
            self.GENERATE_URL,
            {"test": self.test.id, "roster": self.roster.id},
            content_type="application/json",
            **self._auth(),
        )
        self.assertEqual(resp.status_code, 403, resp.content)

    def test_gate_5th_generation_allowed(self):
        """Exactly 4 prior events → 5th generation should succeed (201)."""
        from omr.models import GenerationEvent

        # Create 4 existing events
        for _ in range(4):
            GenerationEvent.objects.create(user=self.user, test=self.test)

        resp = self.client.post(
            self.GENERATE_URL,
            {"test": self.test.id, "roster": self.roster.id},
            content_type="application/json",
            **self._auth(),
        )
        self.assertEqual(resp.status_code, 201, resp.content)

    # ---- cross-tenant isolation ------------------------------------------

    def test_cross_tenant_test_returns_400(self):
        """Using another user's test → 400."""
        resp = self.client.post(
            self.GENERATE_URL,
            {"test": self.other_test.id, "roster": self.roster.id},
            content_type="application/json",
            **self._auth(),
        )
        self.assertEqual(resp.status_code, 400, resp.content)

    def test_cross_tenant_roster_returns_400(self):
        """Using another user's roster → 400."""
        resp = self.client.post(
            self.GENERATE_URL,
            {"test": self.test.id, "roster": self.other_roster.id},
            content_type="application/json",
            **self._auth(),
        )
        self.assertEqual(resp.status_code, 400, resp.content)

    # ---- GET /api/v1/omr/sheets/ -----------------------------------------

    def test_list_sheets_requires_auth(self):
        resp = self.client.get(f"{self.SHEETS_URL}?test={self.test.id}")
        self.assertIn(resp.status_code, [401, 403])

    def test_list_sheets_scoped_to_user(self):
        """After generating, list endpoint returns only the user's sheets."""
        from omr.models import OmrSheet
        # Generate sheets first
        self.client.post(
            self.GENERATE_URL,
            {"test": self.test.id, "roster": self.roster.id},
            content_type="application/json",
            **self._auth(),
        )
        resp = self.client.get(
            f"{self.SHEETS_URL}?test={self.test.id}",
            **self._auth(),
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        data = resp.json()
        # All returned sheets must belong to this test
        sheet_ids = [str(s["id"]) for s in data.get("results", data)]
        db_ids = {
            str(i)
            for i in OmrSheet.objects.filter(test=self.test).values_list("id", flat=True)
        }
        self.assertTrue(sheet_ids, "Expected at least one sheet back")
        for sid in sheet_ids:
            self.assertIn(sid, db_ids)

    def test_list_sheets_not_visible_to_other_user(self):
        """Sheets belonging to self.user are not returned to other_user."""
        from omr.models import OmrSheet
        # Generate for self.user
        self.client.post(
            self.GENERATE_URL,
            {"test": self.test.id, "roster": self.roster.id},
            content_type="application/json",
            **self._auth(),
        )
        # Query as other_user for self.test
        resp = self.client.get(
            f"{self.SHEETS_URL}?test={self.test.id}",
            **self._auth(user=self.other_user),
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        data = resp.json()
        results = data.get("results", data)
        self.assertEqual(len(results), 0, "Other user must not see sheets belonging to this user")
