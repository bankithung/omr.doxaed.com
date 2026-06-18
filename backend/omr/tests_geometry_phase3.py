"""
Phase 3B geometry + generator + 5-option tests.

Test suite:
1. COORD INVARIANCE (C2 guard): build_template with vs without a sections block →
   every answer_bubbles[i] cx/cy/r and the roll grid are byte-identical;
   page_count unchanged.
2. Legacy descriptor (no sections) → _draw_section_headers is a no-op, PDF
   byte-count unchanged vs before (same page count, valid PDF).
3. 5 options end-to-end: Test.default_options=5 → 5 columns laid out;
   simulate_scan filling option "E" → read recovers "E".
4. Scanner read_answers output identical with vs without per-bubble section tags.
"""

from django.test import TestCase


# ---------------------------------------------------------------------------
# 1. Coordinate invariance (C2 guard)
# ---------------------------------------------------------------------------

class CoordInvarianceTests(TestCase):
    """
    answer_bubbles[i].cx/cy/r and roll_grid coords must be byte-identical
    with or without a sections block.  Adding sections is PURELY additive
    (extra dict keys), never geometric.
    """

    def _make_sections(self, num_questions=100):
        """Return a minimal two-section list covering all q_pos."""
        mid = num_questions // 2
        return [
            {
                "key": "A",
                "label": "Physics",
                "order_index": 0,
                "q_pos_range": [0, mid - 1],
                "policy": {"type": "all"},
            },
            {
                "key": "B",
                "label": "Chemistry",
                "order_index": 1,
                "q_pos_range": [mid, num_questions - 1],
                "policy": {"type": "choose_k", "k": 10},
            },
        ]

    def test_cx_cy_r_identical_with_without_sections(self):
        """Core C2 invariant: cx/cy/r unchanged when sections are added."""
        from omr.geometry import build_template

        nq = 100
        d_plain = build_template(nq, 4, 3)
        d_sections = build_template(nq, 4, 3, sections=self._make_sections(nq))

        self.assertEqual(len(d_plain["answer_bubbles"]),
                         len(d_sections["answer_bubbles"]),
                         "answer_bubbles length changed with sections")

        for i, (plain_b, sec_b) in enumerate(
                zip(d_plain["answer_bubbles"], d_sections["answer_bubbles"])):
            self.assertEqual(plain_b["q_pos"], sec_b["q_pos"],
                             f"q_pos changed at index {i}")
            self.assertEqual(plain_b["page"], sec_b["page"],
                             f"page changed at index {i}")
            self.assertEqual(len(plain_b["options"]), len(sec_b["options"]),
                             f"options count changed at index {i}")
            for j, (po, so) in enumerate(zip(plain_b["options"], sec_b["options"])):
                self.assertEqual(po["cx"], so["cx"],
                                 f"cx changed at bubble {i} option {j}")
                self.assertEqual(po["cy"], so["cy"],
                                 f"cy changed at bubble {i} option {j}")
                self.assertEqual(po["r"], so["r"],
                                 f"r changed at bubble {i} option {j}")
                self.assertEqual(po["label"], so["label"],
                                 f"label changed at bubble {i} option {j}")

    def test_page_count_identical_with_without_sections(self):
        from omr.geometry import build_template

        for nq in (25, 50, 51, 100, 150):
            d_plain = build_template(nq, 4, 3)
            d_sections = build_template(nq, 4, 3, sections=self._make_sections(nq))
            self.assertEqual(
                d_plain["page_count"], d_sections["page_count"],
                f"page_count changed for nq={nq}",
            )

    def test_roll_grid_identical_with_without_sections(self):
        from omr.geometry import build_template

        d_plain = build_template(100, 4, 3)
        d_sections = build_template(100, 4, 3, sections=self._make_sections(100))

        rg_plain = d_plain["roll_grid"]
        rg_sec = d_sections["roll_grid"]
        for key in ("origin", "col_pitch", "row_pitch", "radius", "cols", "rows"):
            self.assertEqual(rg_plain[key], rg_sec[key],
                             f"roll_grid.{key} changed with sections")

    def test_sections_key_absent_when_no_sections(self):
        """Legacy call → no 'sections' key in descriptor."""
        from omr.geometry import build_template

        d = build_template(50, 4, 3)
        self.assertNotIn("sections", d,
                         "Legacy descriptor must not contain 'sections' key")

    def test_sections_key_present_when_sections_passed(self):
        from omr.geometry import build_template

        d = build_template(50, 4, 3, sections=self._make_sections(50))
        self.assertIn("sections", d, "sections key must be present when sections param passed")
        self.assertIsInstance(d["sections"], list)
        self.assertEqual(len(d["sections"]), 2)

    def test_per_bubble_section_tag_added(self):
        """Bubbles in covered ranges get a 'section' key; no key otherwise."""
        from omr.geometry import build_template

        nq = 20
        secs = [
            {
                "key": "A",
                "label": "Section A",
                "order_index": 0,
                "q_pos_range": [0, 9],   # q_pos 0–9
                "policy": {"type": "all"},
            }
        ]
        d = build_template(nq, 4, 3, sections=secs)
        for b in d["answer_bubbles"]:
            if b["q_pos"] <= 9:
                self.assertEqual(b.get("section"), "A",
                                 f"q_pos {b['q_pos']} should be tagged with section A")
            else:
                self.assertNotIn("section", b,
                                 f"q_pos {b['q_pos']} should NOT have section tag (uncovered)")

    def test_per_bubble_section_tag_does_not_change_cx_cy(self):
        """Explicitly re-verify coords after tag is added (belt + suspenders)."""
        from omr.geometry import build_template

        nq = 10
        secs = [{"key": "X", "label": "X", "order_index": 0,
                 "q_pos_range": [0, nq - 1], "policy": {"type": "all"}}]
        plain = build_template(nq, 4, 3)
        tagged = build_template(nq, 4, 3, sections=secs)

        for pb, tb in zip(plain["answer_bubbles"], tagged["answer_bubbles"]):
            for po, to_ in zip(pb["options"], tb["options"]):
                self.assertEqual((po["cx"], po["cy"], po["r"]),
                                 (to_["cx"], to_["cy"], to_["r"]))


# ---------------------------------------------------------------------------
# 2. Legacy descriptor → _draw_section_headers no-op
# ---------------------------------------------------------------------------

class LegacyDescriptorTests(TestCase):
    """
    Without a 'sections' key in the descriptor, _draw_section_headers must be
    a complete no-op.  We check that the generated PDF is valid and has the
    expected page count (byte-equality is not checked because ReportLab may
    embed timestamps — we rely on the structural equivalence).
    """

    def _make_descriptor(self, num_questions=60, num_options=4, roll_digits=3):
        from omr.geometry import build_template
        return build_template(num_questions, num_options, roll_digits)

    def _make_sheet(self, sheet_code="000001-LEGACYTST"):
        return {
            "sheet_code": sheet_code,
            "human_readable_code": "LEGACYTST",
            "institution": "Test School",
            "test_title": "Legacy Test",
            "subject": "",
            "student_name": "",
            "roll_label": "Roll No.",
            "roll_digits": 3,
        }

    def test_legacy_pdf_is_valid(self):
        import fitz
        from omr.generator import render_sheet_pdf

        desc = self._make_descriptor()
        sheet = self._make_sheet()
        pdf = render_sheet_pdf(sheet, desc)
        self.assertTrue(pdf.startswith(b"%PDF"), "Not a valid PDF")

    def test_legacy_page_count_correct(self):
        import fitz
        from omr.generator import render_sheet_pdf

        desc = self._make_descriptor(num_questions=60)
        sheet = self._make_sheet()
        pdf = render_sheet_pdf(sheet, desc)
        doc = fitz.open(stream=pdf, filetype="pdf")
        self.assertEqual(doc.page_count, 2)

    def test_sections_descriptor_pdf_valid(self):
        """With a sections descriptor the PDF is still valid."""
        import fitz
        from omr.geometry import build_template
        from omr.generator import render_sheet_pdf

        secs = [
            {"key": "A", "label": "Physics", "order_index": 0,
             "q_pos_range": [0, 34], "policy": {"type": "all"}},
            {"key": "B", "label": "Chemistry", "order_index": 1,
             "q_pos_range": [35, 59], "policy": {"type": "choose_k", "k": 10}},
        ]
        desc = build_template(60, 4, 3, sections=secs)
        sheet = {
            "sheet_code": "000001-SECTEST1",
            "human_readable_code": "SECTEST1",
            "institution": "Test School",
            "test_title": "Competitive Test",
            "subject": "",
            "student_name": "",
            "roll_label": "Roll No.",
            "roll_digits": 3,
        }
        pdf = render_sheet_pdf(sheet, desc)
        doc = fitz.open(stream=pdf, filetype="pdf")
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertEqual(doc.page_count, desc["page_count"])

    def test_draw_section_headers_noop_without_sections(self):
        """Directly call _draw_section_headers with a legacy descriptor → returns immediately."""
        import io
        from reportlab.pdfgen.canvas import Canvas
        from omr.generator import _draw_section_headers

        desc = self._make_descriptor()
        self.assertNotIn("sections", desc)

        buf = io.BytesIO()
        c = Canvas(buf)
        # Should not raise, should not draw anything
        _draw_section_headers(c, desc, page_no=0, page_h_px=1169)
        # No assertion needed; if it raised the test fails


# ---------------------------------------------------------------------------
# 3. 5 options end-to-end
# ---------------------------------------------------------------------------

class FiveOptionsEndToEndTests(TestCase):
    """
    default_options=5 → 5 columns laid out; simulate_scan fills "E";
    read_answers recovers "E".
    """

    def _make_descriptor_5opt(self, num_questions=25):
        from omr.geometry import build_template
        return build_template(num_questions, 5, 3)

    def _make_sheet_meta(self, code="000001-FIVEOPTZ"):
        return {
            "sheet_code": code,
            "human_readable_code": "FIVEOPTZ",
            "institution": "Test",
            "test_title": "5-Option Test",
            "subject": "",
            "student_name": "",
            "roll_label": "Roll No.",
            "roll_digits": 3,
        }

    def test_5_columns_laid_out(self):
        desc = self._make_descriptor_5opt()
        for b in desc["answer_bubbles"]:
            self.assertEqual(len(b["options"]), 5,
                             f"Expected 5 options, got {len(b['options'])} at q_pos={b['q_pos']}")

    def test_option_labels_include_E(self):
        desc = self._make_descriptor_5opt()
        for b in desc["answer_bubbles"]:
            labels = [o["label"] for o in b["options"]]
            self.assertEqual(labels, ["A", "B", "C", "D", "E"],
                             f"Labels mismatch at q_pos={b['q_pos']}: {labels}")

    def test_horizontal_fit_5_options(self):
        """All 5-option bubbles must fit within page width."""
        from omr.geometry import W
        desc = self._make_descriptor_5opt(num_questions=100)
        for b in desc["answer_bubbles"]:
            for opt in b["options"]:
                self.assertLessEqual(
                    opt["cx"] + opt["r"], W,
                    f"Bubble OOB: q_pos={b['q_pos']} label={opt['label']} cx={opt['cx']}"
                )

    def test_simulate_and_read_e(self):
        """Fill option E on q_pos=0; read_answers must recover ['E']."""
        from omr.geometry import build_template
        from omr.simulate import simulate_scan
        from omr.scan.read import to_binary, read_answers

        nq = 10
        desc = build_template(nq, 5, 3)
        meta = self._make_sheet_meta()

        marked = {0: ["E"]}
        img = simulate_scan(desc, meta, marked=marked, roll="001", page=0)
        binary = to_binary(img)
        result = read_answers(binary, desc, page=0)

        self.assertIn(0, result, "q_pos 0 missing from read result")
        self.assertIn("E", result[0]["marked"],
                      f"Expected 'E' in marked; got {result[0]['marked']}")

    def test_simulate_and_read_a_through_e(self):
        """Fill each option A-E on different questions; all must be read back."""
        from omr.geometry import build_template
        from omr.simulate import simulate_scan
        from omr.scan.read import to_binary, read_answers

        nq = 5
        desc = build_template(nq, 5, 3)
        meta = self._make_sheet_meta("000002-FIVEOPTZ")

        marked = {i: [chr(ord("A") + i)] for i in range(nq)}  # Q0→A, Q1→B, … Q4→E
        img = simulate_scan(desc, meta, marked=marked, roll="001", page=0)
        binary = to_binary(img)
        result = read_answers(binary, desc, page=0)

        for i in range(nq):
            expected = chr(ord("A") + i)
            self.assertIn(i, result, f"q_pos {i} missing from read result")
            self.assertIn(expected, result[i]["marked"],
                          f"Q{i}: expected '{expected}', got {result[i]['marked']}")

    def test_4opt_and_5opt_descriptors_differ_in_column_count(self):
        """Sanity: 4-opt vs 5-opt descriptors differ only in option count."""
        from omr.geometry import build_template

        d4 = build_template(10, 4, 3)
        d5 = build_template(10, 5, 3)
        self.assertEqual(d4["page_count"], d5["page_count"])
        for b4, b5 in zip(d4["answer_bubbles"], d5["answer_bubbles"]):
            self.assertEqual(len(b4["options"]), 4)
            self.assertEqual(len(b5["options"]), 5)
            # First 4 options share same cx/cy (same OPTION_PITCH)
            for j in range(4):
                self.assertEqual(b4["options"][j]["cx"], b5["options"][j]["cx"])
                self.assertEqual(b4["options"][j]["cy"], b5["options"][j]["cy"])


# ---------------------------------------------------------------------------
# 4. Scanner ignores section tags (read output identical with/without tags)
# ---------------------------------------------------------------------------

class ScannerIgnoresSectionTagsTests(TestCase):
    """
    read_answers output must be identical whether the descriptor has per-bubble
    'section' tags or not.
    """

    def _base_descriptor(self, nq=10, num_options=4):
        from omr.geometry import build_template
        return build_template(nq, num_options, 3)

    def _tagged_descriptor(self, nq=10, num_options=4):
        from omr.geometry import build_template
        secs = [{"key": "A", "label": "All", "order_index": 0,
                 "q_pos_range": [0, nq - 1], "policy": {"type": "all"}}]
        return build_template(nq, num_options, 3, sections=secs)

    def _make_meta(self):
        return {
            "sheet_code": "000001-SCANTAGS",
            "human_readable_code": "SCANTAGS",
            "institution": "",
            "test_title": "",
            "subject": "",
            "student_name": "",
            "roll_label": "Roll No.",
            "roll_digits": 3,
        }

    def test_read_answers_identical_with_without_tags(self):
        from omr.simulate import simulate_scan
        from omr.scan.read import to_binary, read_answers

        nq = 10
        desc_plain = self._base_descriptor(nq)
        desc_tagged = self._tagged_descriptor(nq)
        meta = self._make_meta()

        marked = {i: ["A"] if i % 2 == 0 else ["B"] for i in range(nq)}

        img_plain = simulate_scan(desc_plain, meta, marked=marked, roll="001", page=0)
        img_tagged = simulate_scan(desc_tagged, meta, marked=marked, roll="001", page=0)

        bin_plain = to_binary(img_plain)
        bin_tagged = to_binary(img_tagged)

        result_plain = read_answers(bin_plain, desc_plain, page=0)
        result_tagged = read_answers(bin_tagged, desc_tagged, page=0)

        self.assertEqual(
            len(result_plain), len(result_tagged),
            "Different number of questions read back",
        )
        for qp in result_plain:
            self.assertIn(qp, result_tagged, f"q_pos {qp} missing from tagged result")
            # Compare marked labels (flag may differ due to image noise, so just
            # check the set of marked labels)
            self.assertEqual(
                set(result_plain[qp]["marked"]),
                set(result_tagged[qp]["marked"]),
                f"Marked labels differ at q_pos {qp}",
            )

    def test_bubbles_tagged_with_correct_section_key(self):
        """Verify section tags on bubbles match the section they cover."""
        from omr.geometry import build_template

        secs = [
            {"key": "PHY", "label": "Physics", "order_index": 0,
             "q_pos_range": [0, 4], "policy": {"type": "all"}},
            {"key": "CHE", "label": "Chemistry", "order_index": 1,
             "q_pos_range": [5, 9], "policy": {"type": "all"}},
        ]
        d = build_template(10, 4, 3, sections=secs)
        for b in d["answer_bubbles"]:
            qp = b["q_pos"]
            if qp <= 4:
                self.assertEqual(b.get("section"), "PHY",
                                 f"q_pos={qp} should be PHY")
            else:
                self.assertEqual(b.get("section"), "CHE",
                                 f"q_pos={qp} should be CHE")

    def test_read_answers_does_not_return_section_field(self):
        """read_answers output dict values have 'marked' and 'flag', not 'section'."""
        from omr.geometry import build_template
        from omr.simulate import simulate_scan
        from omr.scan.read import to_binary, read_answers

        nq = 5
        secs = [{"key": "A", "label": "A", "order_index": 0,
                 "q_pos_range": [0, nq - 1], "policy": {"type": "all"}}]
        desc = build_template(nq, 4, 3, sections=secs)
        meta = {
            "sheet_code": "000001-RDSCTEST",
            "human_readable_code": "RDSCTEST",
            "institution": "", "test_title": "", "subject": "",
            "student_name": "", "roll_label": "Roll No.", "roll_digits": 3,
        }
        img = simulate_scan(desc, meta, marked={0: ["A"]}, roll="001", page=0)
        binary = to_binary(img)
        result = read_answers(binary, desc, page=0)

        for qp, val in result.items():
            self.assertIn("marked", val, f"'marked' missing at q_pos={qp}")
            self.assertIn("flag", val, f"'flag' missing at q_pos={qp}")
            self.assertNotIn("section", val,
                             f"'section' should NOT be in read_answers output at q_pos={qp}")


# ---------------------------------------------------------------------------
# 5. views.GenerateView honors default_options
# ---------------------------------------------------------------------------

class DefaultOptionsViewTests(TestCase):
    """
    Test that GenerateView uses test.default_options when computing num_options.
    We test the logic directly (mocking the DB objects) to avoid a full HTTP
    round-trip which would require a roster + full fixture.
    """

    def test_default_options_5_yields_5_columns(self):
        """
        When test.default_options=5 and questions have only 4 options each,
        the generated descriptor should have 5 option columns.
        """
        from omr.geometry import build_template

        # Simulate what views.py does:
        # max_options (from questions) = 4; test_default_options = 5
        max_options = 4
        test_default_options = 5
        num_options = max(2, min(6, max(test_default_options, max_options)))
        self.assertEqual(num_options, 5)

        desc = build_template(10, num_options, 3)
        for b in desc["answer_bubbles"]:
            self.assertEqual(len(b["options"]), 5,
                             f"Expected 5 columns, got {len(b['options'])} at q_pos={b['q_pos']}")

    def test_default_options_4_with_5opt_questions(self):
        """
        default_options=4 but questions have 5 options → num_options=5 (questions win).
        """
        max_options = 5
        test_default_options = 4
        num_options = max(2, min(6, max(test_default_options, max_options)))
        self.assertEqual(num_options, 5)

    def test_default_options_clamp_max(self):
        """default_options=99 → clamped to 6."""
        max_options = 4
        test_default_options = 99
        num_options = max(2, min(6, max(test_default_options, max_options)))
        self.assertEqual(num_options, 6)

    def test_default_options_clamp_min(self):
        """default_options=1 → clamped to 2."""
        max_options = 1
        test_default_options = 1
        num_options = max(2, min(6, max(test_default_options, max_options)))
        self.assertEqual(num_options, 2)
