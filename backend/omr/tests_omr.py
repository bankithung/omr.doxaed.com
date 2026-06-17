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
