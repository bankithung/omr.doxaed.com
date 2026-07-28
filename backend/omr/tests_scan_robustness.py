"""
Regression tests for the scan pipeline's failure modes.

Each test here corresponds to a defect that shipped and was found by
`manage.py scan_bench`. They are cheap, deterministic reproductions of the
conditions in that corpus, so a regression fails CI rather than a benchmark
somebody has to remember to run.
"""

from django.test import SimpleTestCase

import cv2
import numpy as np

from omr.geometry import build_template
from omr.scan import degrade as dg
from omr.scan.align import (
    crop_to_page,
    decode_qr_from_canonical,
    detect_fiducials,
    warp_to_canonical,
)
from omr.scan.pipeline import process_image
from omr.scan.read import read_answers, registration_score
from omr import bench


def _sheet(seed=7, **mark_kw):
    rng = np.random.default_rng(seed)
    return bench.build_bench_sheet(rng, **mark_kw)


def _graded(out):
    """True when the pipeline was willing to grade, rather than refusing."""
    flags = set(out.get("flags") or [])
    return bool(out.get("reads")) and not (flags & {"no_qr", "alignment", "all_blank"})


def _accuracy(out, truth):
    reads = out.get("reads") or {}
    ok = sum(
        1 for q, want in truth.items()
        if sorted((reads.get(q) or {}).get("marked", [])) == sorted(want)
    )
    return ok / len(truth) if truth else 0.0


def _silently_wrong(out, truth):
    """
    Answers that were GRADED, are wrong, and carry no flag.

    A refused sheet scores zero here by definition. Refusing is the safe
    outcome and must not be conflated with grading something wrong, which is
    the opposite behaviour.
    """
    if not _graded(out):
        return 0
    reads = out.get("reads") or {}
    n = 0
    for q, want in truth.items():
        e = reads.get(q) or {}
        if sorted(e.get("marked", [])) != sorted(want) and not e.get("flag"):
            n += 1
    return n


class SurfaceAndAngleTests(SimpleTestCase):
    """The frame contains a desk, which used to dissolve every fiducial."""

    def test_reads_on_a_dark_surface(self):
        img, desc, truth = _sheet()
        rng = np.random.default_rng(3)
        out = process_image(dg.cap_on_surface(img, surface=40, rng=rng), desc)
        self.assertTrue(_graded(out), "a page on a dark desk must still grade")
        self.assertEqual(_accuracy(out, truth), 1.0)

    def test_reads_at_a_handheld_angle(self):
        img, desc, truth = _sheet()
        rng = np.random.default_rng(3)
        damaged = dg.cap_on_surface(img, surface=110, keystone=0.20,
                                    rotate_deg=-5.0, rng=rng)
        out = process_image(damaged, desc)
        self.assertTrue(_graded(out), "perspective must be corrected, not assumed away")
        self.assertEqual(_accuracy(out, truth), 1.0)


class IlluminationTests(SimpleTestCase):
    """One flat-field pass has to cover shadow, vignetting and underexposure."""

    def test_reads_under_a_shadow(self):
        img, desc, truth = _sheet(ink=dg.INK_PENCIL_HB)
        out = process_image(dg.cap_shadow(img, strength=0.6, angle_deg=35), desc)
        self.assertTrue(_graded(out))
        self.assertEqual(_accuracy(out, truth), 1.0)

    def test_reads_in_low_light(self):
        img, desc, truth = _sheet(ink=dg.INK_PENCIL_HB)
        rng = np.random.default_rng(3)
        dark = dg.cap_noise(dg.cap_low_light(img, gain=0.30, gamma=1.7), 10, rng)
        out = process_image(dark, desc)
        self.assertTrue(_graded(out))
        self.assertEqual(_accuracy(out, truth), 1.0)


class FaintMarkTests(SimpleTestCase):
    """
    Light pencil used to be scored as blank at full confidence, because the
    reader binarised before measuring.
    """

    def test_light_pencil_is_read_not_dropped(self):
        img, desc, truth = _sheet(ink=dg.INK_PENCIL_LIGHT)
        out = process_image(img, desc)
        self.assertTrue(_graded(out))
        self.assertEqual(_accuracy(out, truth), 1.0)
        self.assertEqual(_silently_wrong(out, truth), 0)

    def test_a_tick_is_not_a_blank(self):
        img, desc, truth = _sheet(ink=dg.INK_BIRO, style="tick")
        out = process_image(img, desc)
        self.assertTrue(_graded(out))
        self.assertEqual(_accuracy(out, truth), 1.0)

    def test_clean_sheet_raises_no_faint_flags(self):
        """
        The option letter is printed inside every bubble, so an untouched
        bubble is not blank paper. Before the per-label baseline that produced
        a run of spurious faint flags on a perfectly clean sheet.
        """
        img, desc, _ = _sheet()
        out = process_image(img, desc)
        self.assertNotIn("faint", out.get("flags") or [])


class OrientationTests(SimpleTestCase):
    """
    Four identical corner squares are rotationally symmetric, so an upside down
    sheet warps perfectly and used to grade against mirrored positions at high
    confidence.
    """

    def test_upside_down_sheet_grades_correctly(self):
        img, desc, truth = _sheet()
        out = process_image(dg.cap_rotate180(img), desc)
        self.assertTrue(_graded(out), "an inverted sheet must be detected and corrected")
        self.assertEqual(_accuracy(out, truth), 1.0)


class RegistrationTests(SimpleTestCase):
    """
    Matching the four corners does not prove the middle matches. A creased
    sheet is not planar, so no homography rectifies it, and it used to be
    graded confidently against the wrong bubbles.
    """

    def test_folded_sheet_is_refused_not_guessed(self):
        img, desc, truth = _sheet(ink=dg.INK_PENCIL_HB)
        rng = np.random.default_rng(3)
        folded = dg.cap_on_surface(dg.cap_fold(img, strength=0.05),
                                   surface=110, keystone=0.10, rng=rng)
        out = process_image(folded, desc)
        self.assertFalse(
            _graded(out),
            "a misregistered page must be refused, never graded against drifted "
            "coordinates",
        )
        self.assertEqual(_silently_wrong(out, truth), 0)

    def test_registration_separates_good_from_drifted(self):
        img, desc, _ = _sheet()
        page = crop_to_page(img, desc)
        pts = detect_fiducials(page, desc)
        self.assertIsNotNone(pts)
        good = warp_to_canonical(page, pts, desc)
        self.assertGreaterEqual(registration_score(good, desc, 0), 0.85)

        # Shift the whole page: every ring moves off its coordinate.
        M = np.float32([[1, 0, 5], [0, 1, 4]])
        drifted = cv2.warpAffine(good, M, (good.shape[1], good.shape[0]),
                                 borderValue=255)
        self.assertLess(registration_score(drifted, desc, 0), 0.85)


class DoubleMarkTests(SimpleTestCase):
    """
    A real double mark is two comparable marks. Dirt beside a solid answer is
    not, and used to send clean sheets to review.
    """

    def test_two_real_marks_are_flagged(self):
        from omr.simulate import simulate_scan
        desc = build_template(num_questions=10, num_options=4, roll_digits=3)
        meta = dict(sheet_code="x-Y", human_readable_code="Y", institution="I",
                    test_title="T", student_name="S", roll_number="042")
        img = simulate_scan(desc, meta, marked={0: ["A", "B"], 1: ["C"]},
                            roll="042", page=0, scale=1.0)
        answers = read_answers(img, desc, page=0)
        self.assertEqual(answers[0]["flag"], "double_mark")
        self.assertEqual(sorted(answers[0]["marked"]), ["A", "B"])
        self.assertIsNone(answers[1]["flag"], "a single mark must not flag")
        self.assertEqual(answers[1]["marked"], ["C"])

    def test_speck_beside_an_answer_is_not_a_double_mark(self):
        img, desc, truth = _sheet(ink=dg.INK_PENCIL_HB)
        rng = np.random.default_rng(5)
        out = process_image(dg.cap_photocopy(img, rng=rng), desc)
        self.assertTrue(_graded(out))
        self.assertEqual(_accuracy(out, truth), 1.0)


class ConfidenceTests(SimpleTestCase):
    """
    Confidence used to be the fraction of unflagged questions, which is 1.0
    precisely when nothing was flagged, including on a page read entirely wrong.
    """

    def test_confidence_is_reported_and_bounded(self):
        img, desc, _ = _sheet()
        out = process_image(img, desc)
        self.assertIn("confidence", out)
        self.assertGreaterEqual(out["confidence"], 0.0)
        self.assertLessEqual(out["confidence"], 1.0)

    def test_unreadable_capture_reports_no_confidence(self):
        desc = build_template(num_questions=10, num_options=4, roll_digits=3)
        blank = np.full((800, 600), 255, dtype=np.uint8)
        out = process_image(blank, desc)
        self.assertEqual(out["confidence"], 0.0)
        self.assertIn("no_qr", out.get("flags") or [])
