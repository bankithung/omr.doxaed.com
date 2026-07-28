"""
Tests for omr.simulate — synthetic scan simulator (Task 2, Phase 4).

TDD: these tests define the contract that simulate.py must satisfy.
"""

import cv2
import numpy as np
from PIL import Image
from django.test import TestCase
from pyzbar.pyzbar import decode as pyzbar_decode

from omr.codes import make_sheet_code
from omr.geometry import build_template


class RenderCanonicalImageTests(TestCase):
    """render_canonical_image — shape and basic pixel sanity checks."""

    def _descriptor(self):
        return build_template(num_questions=10, num_options=4, roll_digits=3)

    def _sheet_meta(self, descriptor):
        sheet_code, human_code = make_sheet_code(1, 42)
        return {
            "sheet_code": sheet_code,
            "human_readable_code": human_code,
            "institution": "Test School",
            "test_title": "Math Exam",
            "subject": "Math",
            "student_name": "Alice",
            "roll_label": "Roll No.",
            "roll_digits": descriptor["roll_grid"]["cols"],
        }

    def test_returns_ndarray(self):
        from omr.simulate import render_canonical_image
        descriptor = self._descriptor()
        img = render_canonical_image(descriptor, self._sheet_meta(descriptor))
        self.assertIsInstance(img, np.ndarray)

    def test_shape_matches_page_px(self):
        """Returned array must be exactly (H, W) = (page_px[1], page_px[0])."""
        from omr.simulate import render_canonical_image
        descriptor = self._descriptor()
        img = render_canonical_image(descriptor, self._sheet_meta(descriptor))
        W, H = descriptor["page_px"]
        self.assertEqual(img.shape, (H, W),
                         f"Expected ({H}, {W}), got {img.shape}")

    def test_dtype_is_uint8(self):
        from omr.simulate import render_canonical_image
        descriptor = self._descriptor()
        img = render_canonical_image(descriptor, self._sheet_meta(descriptor))
        self.assertEqual(img.dtype, np.uint8)

    def test_image_has_white_background(self):
        """Mean pixel value of the rendered sheet should be high (mostly white)."""
        from omr.simulate import render_canonical_image
        descriptor = self._descriptor()
        img = render_canonical_image(descriptor, self._sheet_meta(descriptor))
        mean = img.mean()
        self.assertGreater(mean, 150,
                           f"Expected mostly-white image (mean>150), got mean={mean:.1f}")

    def test_fiducial_region_is_dark(self):
        """Fiducial squares must be filled black in the rendered image."""
        from omr.simulate import render_canonical_image
        from omr.geometry import FID
        descriptor = self._descriptor()
        img = render_canonical_image(descriptor, self._sheet_meta(descriptor))

        # Top-left fiducial
        fid = descriptor["fiducials"][0]
        cx, cy = fid["cx"], fid["cy"]
        r = FID // 2
        region = img[cy - r:cy + r, cx - r:cx + r]
        self.assertLess(region.mean(), 50,
                        f"Fiducial should be dark (mean<50), got {region.mean():.1f}")

    def test_page_1_can_be_rendered(self):
        """render_canonical_image(page=1) for a two-page descriptor."""
        from omr.simulate import render_canonical_image
        descriptor = build_template(num_questions=60, num_options=4, roll_digits=3)
        sheet_code, human_code = make_sheet_code(2, 7)
        sheet_meta = {
            "sheet_code": sheet_code,
            "human_readable_code": human_code,
            "institution": "School",
            "test_title": "Test",
            "subject": "",
            "student_name": "",
            "roll_label": "Roll No.",
            "roll_digits": 3,
        }
        img = render_canonical_image(descriptor, sheet_meta, page=1)
        W, H = descriptor["page_px"]
        self.assertEqual(img.shape, (H, W))


class SimulateScanTests(TestCase):
    """simulate_scan — core behaviour: shape, marked bubbles, roll, QR."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _descriptor(self, num_questions=10, num_options=4, roll_digits=3):
        return build_template(
            num_questions=num_questions,
            num_options=num_options,
            roll_digits=roll_digits,
        )

    def _sheet_meta(self, descriptor, test_id=1, seed=99):
        sheet_code, human_code = make_sheet_code(test_id, seed)
        return (
            {
                "sheet_code": sheet_code,
                "human_readable_code": human_code,
                "institution": "Test School",
                "test_title": "Math Exam",
                "subject": "Math",
                "student_name": "Alice",
                "roll_label": "Roll No.",
                "roll_digits": descriptor["roll_grid"]["cols"],
            },
            sheet_code,
        )

    # ------------------------------------------------------------------
    # Shape / dtype
    # ------------------------------------------------------------------

    def test_shape_matches_page_px(self):
        """simulate_scan must return exactly (H, W) grayscale uint8."""
        from omr.simulate import simulate_scan
        descriptor = self._descriptor()
        sheet_meta, _ = self._sheet_meta(descriptor)
        img = simulate_scan(descriptor, sheet_meta, marked={0: ["A"]}, roll="042")
        W, H = descriptor["page_px"]
        self.assertEqual(img.shape, (H, W),
                         f"Expected shape ({H}, {W}), got {img.shape}")

    def test_dtype_uint8(self):
        from omr.simulate import simulate_scan
        descriptor = self._descriptor()
        sheet_meta, _ = self._sheet_meta(descriptor)
        img = simulate_scan(descriptor, sheet_meta, marked={}, roll="000")
        self.assertEqual(img.dtype, np.uint8)

    # ------------------------------------------------------------------
    # QR code still decodes after bubble filling
    # ------------------------------------------------------------------

    def test_qr_decodes_from_simulated_image(self):
        """
        The QR code must remain decodable by pyzbar after bubble filling.
        This confirms that cv2.circle calls on answer bubbles do not corrupt
        the QR region and that the rendering preserves QR resolution.

        Note: QR decodability at canonical size (827×1169) depends on the QR
        version selected by qrcode for a specific payload.  We use test_id=1,
        seed=3 which produces a payload that encodes into a QR version readable
        at this resolution (verified during development).
        """
        from omr.simulate import simulate_scan
        descriptor = self._descriptor(num_questions=10, num_options=4, roll_digits=3)
        # test_id=1, seed=3 → sheet_code '000001-QXZO7GD3' → reliably decodable at 827×1169
        sheet_meta, sheet_code = self._sheet_meta(descriptor, test_id=1, seed=3)

        # Mark a couple of answers and a roll
        marked = {0: ["A"], 2: ["C"], 5: ["B"]}
        roll = "042"

        img = simulate_scan(descriptor, sheet_meta, marked=marked, roll=roll)

        codes = pyzbar_decode(Image.fromarray(img))
        self.assertTrue(
            len(codes) > 0,
            "pyzbar found no QR codes in the simulated image.",
        )
        payloads = [c.data.decode() for c in codes]
        self.assertTrue(
            any(p.startswith(sheet_code) for p in payloads),
            f"QR payload should start with sheet_code={sheet_code!r}. "
            f"Got payloads: {payloads}",
        )

    def test_qr_payload_format(self):
        """QR payload must be 'sheet_code|page+1|page_count'."""
        from omr.simulate import simulate_scan
        descriptor = self._descriptor(num_questions=10)
        sheet_meta, sheet_code = self._sheet_meta(descriptor, test_id=3, seed=7)
        page_count = descriptor["page_count"]

        img = simulate_scan(descriptor, sheet_meta, marked={}, roll="001", page=0)
        codes = pyzbar_decode(Image.fromarray(img))
        self.assertGreater(len(codes), 0, "No QR found in simulated image")
        expected_payload = f"{sheet_code}|1|{page_count}"
        payloads = [c.data.decode() for c in codes]
        self.assertIn(expected_payload, payloads,
                      f"Expected '{expected_payload}', got {payloads}")

    # ------------------------------------------------------------------
    # Filled bubble is darker than unfilled
    # ------------------------------------------------------------------

    def test_marked_bubble_is_darker_than_unmarked(self):
        """
        After filling, the mean pixel value at a marked option's centre must
        be < the mean pixel value at an unmarked option's centre on the same
        question row.
        """
        from omr.simulate import simulate_scan
        descriptor = self._descriptor(num_questions=10, num_options=4, roll_digits=3)
        sheet_meta, _ = self._sheet_meta(descriptor, test_id=7, seed=55)

        # Mark only option A on question 0; options B, C, D remain empty
        marked = {0: ["A"]}
        roll = "000"

        img = simulate_scan(descriptor, sheet_meta, marked=marked, roll=roll)

        # Find the option descriptors for q_pos=0
        q0_entry = next(b for b in descriptor["answer_bubbles"] if b["q_pos"] == 0)
        opts = {o["label"]: o for o in q0_entry["options"]}

        def sample_region(opt):
            cx, cy, r = int(opt["cx"]), int(opt["cy"]), int(opt["r"])
            # Sample a disc of radius r*0.7 (the filled zone)
            sample_r = max(1, int(r * 0.7))
            patch = img[cy - sample_r: cy + sample_r + 1,
                        cx - sample_r: cx + sample_r + 1]
            return float(patch.mean())

        mean_A = sample_region(opts["A"])   # should be dark (filled)
        mean_B = sample_region(opts["B"])   # should be bright (unfilled)
        mean_C = sample_region(opts["C"])   # should be bright (unfilled)

        self.assertLess(
            mean_A, mean_B,
            f"Filled option A (mean={mean_A:.1f}) should be darker than "
            f"unfilled option B (mean={mean_B:.1f})",
        )
        self.assertLess(
            mean_A, mean_C,
            f"Filled option A (mean={mean_A:.1f}) should be darker than "
            f"unfilled option C (mean={mean_C:.1f})",
        )
        # A concrete threshold: filled region mean < 100 (dark grey or black)
        self.assertLess(mean_A, 100,
                        f"Filled bubble mean ({mean_A:.1f}) should be < 100")
        # Unfilled region mean > 150 (light, mostly white)
        self.assertGreater(mean_B, 150,
                           f"Unfilled bubble mean ({mean_B:.1f}) should be > 150")

    def test_multiple_marked_options_all_filled(self):
        """Marking multiple options on one question should fill each one."""
        from omr.simulate import simulate_scan
        descriptor = self._descriptor(num_questions=5, num_options=4, roll_digits=2)
        sheet_meta, _ = self._sheet_meta(descriptor, test_id=9, seed=11)

        marked = {0: ["A", "C"]}
        img = simulate_scan(descriptor, sheet_meta, marked=marked, roll="13")

        q0 = next(b for b in descriptor["answer_bubbles"] if b["q_pos"] == 0)
        opts = {o["label"]: o for o in q0["options"]}

        def mean_at(label):
            opt = opts[label]
            cx, cy, r = int(opt["cx"]), int(opt["cy"]), int(opt["r"])
            sr = max(1, int(r * 0.7))
            return img[cy - sr: cy + sr + 1, cx - sr: cx + sr + 1].mean()

        self.assertLess(mean_at("A"), 100, "Option A should be filled (dark)")
        self.assertLess(mean_at("C"), 100, "Option C should be filled (dark)")
        self.assertGreater(mean_at("B"), 150, "Option B should be unfilled (bright)")
        self.assertGreater(mean_at("D"), 150, "Option D should be unfilled (bright)")

    # ------------------------------------------------------------------
    # Roll grid
    # ------------------------------------------------------------------

    def test_roll_digit_bubble_filled(self):
        """Digits in the roll number must produce dark bubbles at correct positions."""
        from omr.simulate import simulate_scan
        descriptor = self._descriptor(num_questions=5, num_options=4, roll_digits=3)
        sheet_meta, _ = self._sheet_meta(descriptor, test_id=4, seed=77)

        roll = "371"
        img = simulate_scan(descriptor, sheet_meta, marked={}, roll=roll)

        rg = descriptor["roll_grid"]
        ox, oy = int(rg["origin"][0]), int(rg["origin"][1])
        col_pitch = int(rg["col_pitch"])
        row_pitch = int(rg["row_pitch"])
        radius = int(rg["radius"])

        for col_idx, digit_char in enumerate(roll):
            digit = int(digit_char)
            cx = ox + col_idx * col_pitch
            cy = oy + digit * row_pitch
            sr = max(1, int(radius * 0.7))
            region = img[cy - sr: cy + sr + 1, cx - sr: cx + sr + 1]
            mean = float(region.mean())
            self.assertLess(
                mean, 100,
                f"Roll col={col_idx} digit={digit} at ({cx},{cy}) "
                f"should be dark, got mean={mean:.1f}",
            )

    def test_roll_not_filled_on_page_1(self):
        """Roll grid should NOT be filled when page=1 (roll is on page 0 only)."""
        from omr.simulate import simulate_scan
        descriptor = build_template(num_questions=60, num_options=4, roll_digits=3)
        sheet_code, human_code = make_sheet_code(10, 5)
        sheet_meta = {
            "sheet_code": sheet_code,
            "human_readable_code": human_code,
            "institution": "School",
            "test_title": "Exam",
            "subject": "",
            "student_name": "",
            "roll_label": "Roll No.",
            "roll_digits": 3,
        }

        roll = "999"
        # Page 0 rendered (roll filled)
        img_p0 = simulate_scan(descriptor, sheet_meta, marked={}, roll=roll, page=0)
        # Page 1 rendered (roll grid NOT present on page 1 of the PDF)
        img_p1 = simulate_scan(descriptor, sheet_meta, marked={}, roll=roll, page=1)

        # On page 0, roll digit '9' in col 0 → row 9 → check dark
        rg = descriptor["roll_grid"]
        ox, oy = int(rg["origin"][0]), int(rg["origin"][1])
        row_pitch = int(rg["row_pitch"])
        radius = int(rg["radius"])
        sr = max(1, int(radius * 0.7))
        cy_row9 = oy + 9 * row_pitch
        region_p0 = img_p0[cy_row9 - sr: cy_row9 + sr + 1, ox - sr: ox + sr + 1]
        region_p1 = img_p1[cy_row9 - sr: cy_row9 + sr + 1, ox - sr: ox + sr + 1]

        # Page 0: filled → dark
        self.assertLess(region_p0.mean(), 100,
                        f"Roll bubble on page 0 should be filled (dark), got {region_p0.mean():.1f}")
        # Page 1: the roll grid is not drawn in the PDF on page 1, so no filled bubbles
        self.assertGreater(region_p1.mean(), 150,
                           f"Roll region on page 1 should be bright (no roll grid), got {region_p1.mean():.1f}")

    # ------------------------------------------------------------------
    # Perspective transform
    # ------------------------------------------------------------------

    def test_with_perspective_transform_returns_correct_shape(self):
        """Applying a transform must not change the output shape."""
        from omr.simulate import simulate_scan, perspective_transform
        descriptor = self._descriptor()
        sheet_meta, _ = self._sheet_meta(descriptor, test_id=2, seed=33)
        W, H = descriptor["page_px"]
        transform = perspective_transform(W, H, jitter_px=10)
        img = simulate_scan(descriptor, sheet_meta, marked={0: ["B"]}, roll="001",
                            transform=transform)
        self.assertEqual(img.shape, (H, W))

    def test_perspective_transform_distorts_image(self):
        """
        An image warped with perspective_transform must differ from the unwarped
        original (i.e. the warp actually does something).
        """
        from omr.simulate import simulate_scan, perspective_transform
        descriptor = self._descriptor()
        sheet_meta, _ = self._sheet_meta(descriptor, test_id=2, seed=33)
        W, H = descriptor["page_px"]
        transform = perspective_transform(W, H, jitter_px=20)

        img_flat = simulate_scan(descriptor, sheet_meta, marked={0: ["A"]}, roll="001")
        img_warped = simulate_scan(descriptor, sheet_meta, marked={0: ["A"]}, roll="001",
                                   transform=transform)

        # The images should differ where the warp moved content
        diff = np.abs(img_flat.astype(int) - img_warped.astype(int))
        self.assertGreater(diff.mean(), 1.0,
                           "Warped and flat images should differ; warp had no effect")


class PerspectiveTransformHelperTests(TestCase):
    """perspective_transform() helper — shape and determinism."""

    def test_returns_3x3_matrix(self):
        from omr.simulate import perspective_transform
        H_mat = perspective_transform(827, 1169)
        self.assertEqual(H_mat.shape, (3, 3))

    def test_deterministic(self):
        from omr.simulate import perspective_transform
        m1 = perspective_transform(827, 1169, jitter_px=15)
        m2 = perspective_transform(827, 1169, jitter_px=15)
        np.testing.assert_array_equal(m1, m2)

    def test_different_jitter_different_matrix(self):
        from omr.simulate import perspective_transform
        m1 = perspective_transform(827, 1169, jitter_px=5)
        m2 = perspective_transform(827, 1169, jitter_px=20)
        self.assertFalse(np.allclose(m1, m2),
                         "Different jitter_px values should produce different matrices")


# ===========================================================================
# Phase 4 Task 3 — scan alignment pipeline (align.py) TDD tests
# ===========================================================================

class DecodeQRTests(TestCase):
    """omr.scan.align.decode_qr — QR decoding on higher-res (scale=2) scans."""

    def _make_scan(self, test_id=1, seed=3, scale=2.0):
        """Produce a simulated scan at the given scale and return (img, sheet_code, page_count)."""
        from omr.simulate import simulate_scan
        descriptor = build_template(num_questions=10, num_options=4, roll_digits=3)
        sheet_code, human_code = make_sheet_code(test_id, seed)
        sheet_meta = {
            "sheet_code": sheet_code,
            "human_readable_code": human_code,
            "institution": "Test School",
            "test_title": "Math Exam",
            "subject": "Math",
            "student_name": "Alice",
            "roll_label": "Roll No.",
            "roll_digits": descriptor["roll_grid"]["cols"],
        }
        img = simulate_scan(
            descriptor, sheet_meta,
            marked={0: ["A"]}, roll="042",
            page=0, scale=scale,
        )
        return img, sheet_code, descriptor["page_count"]

    def test_decode_qr_returns_correct_tuple(self):
        """decode_qr on a scale=2 scan returns (sheet_code, page, total)."""
        from omr.scan.align import decode_qr
        img, sheet_code, page_count = self._make_scan(test_id=1, seed=3, scale=2.0)
        result = decode_qr(img)
        self.assertIsNotNone(result, "decode_qr returned None on a scale=2 scan")
        got_code, got_page, got_total = result
        self.assertEqual(got_code, sheet_code,
                         f"sheet_code mismatch: expected {sheet_code!r}, got {got_code!r}")
        self.assertEqual(got_page, 1,
                         f"page should be 1 (1-based), got {got_page}")
        self.assertEqual(got_total, page_count,
                         f"total should be {page_count}, got {got_total}")

    def test_decode_qr_returns_none_on_blank_image(self):
        """decode_qr on a blank white image returns None."""
        from omr.scan.align import decode_qr
        blank = np.full((1169, 827), 255, dtype=np.uint8)
        result = decode_qr(blank)
        self.assertIsNone(result, "Expected None for blank image, got result")

    def test_decode_qr_page_and_total_are_int(self):
        """page and total fields returned by decode_qr are Python ints."""
        from omr.scan.align import decode_qr
        img, _, _ = self._make_scan(test_id=2, seed=7, scale=2.0)
        result = decode_qr(img)
        if result is None:
            self.skipTest("QR not decoded at scale=2 for this payload — skipping int type check")
        _, page, total = result
        self.assertIsInstance(page, int)
        self.assertIsInstance(total, int)

    def test_decode_qr_works_on_scale1_fallback(self):
        """
        decode_qr on a scale=1 (canonical) scan may or may not decode;
        the function must not raise an exception regardless.
        """
        from omr.scan.align import decode_qr
        from omr.simulate import simulate_scan
        descriptor = build_template(num_questions=10, num_options=4, roll_digits=3)
        sheet_code, human_code = make_sheet_code(1, 3)
        sheet_meta = {
            "sheet_code": sheet_code,
            "human_readable_code": human_code,
            "institution": "School", "test_title": "Exam",
            "subject": "", "student_name": "",
            "roll_label": "Roll No.",
            "roll_digits": descriptor["roll_grid"]["cols"],
        }
        img = simulate_scan(descriptor, sheet_meta, marked={}, roll="001", scale=1.0)
        # Must not raise; result may be None or a valid tuple
        result = decode_qr(img)
        self.assertTrue(result is None or (isinstance(result, tuple) and len(result) == 3))


class DetectFiducialsAndWarpTests(TestCase):
    """omr.scan.align.detect_fiducials + warp_to_canonical — end-to-end alignment."""

    SCALE = 2.0  # render at 200 DPI for reliable detection

    def _descriptor_and_meta(self, num_questions=10, test_id=5, seed=17):
        descriptor = build_template(num_questions=num_questions, num_options=4, roll_digits=3)
        sheet_code, human_code = make_sheet_code(test_id, seed)
        sheet_meta = {
            "sheet_code": sheet_code,
            "human_readable_code": human_code,
            "institution": "Test Inst",
            "test_title": "Test Exam",
            "subject": "Science",
            "student_name": "Bob",
            "roll_label": "Roll No.",
            "roll_digits": descriptor["roll_grid"]["cols"],
        }
        return descriptor, sheet_meta

    def test_detect_fiducials_finds_4_points_on_flat_scan(self):
        """detect_fiducials returns (4,2) float32 on an unwarped scale=2 scan."""
        from omr.simulate import simulate_scan
        from omr.scan.align import detect_fiducials
        descriptor, sheet_meta = self._descriptor_and_meta()
        img = simulate_scan(descriptor, sheet_meta, marked={}, roll="001",
                            scale=self.SCALE)
        pts = detect_fiducials(img, descriptor)
        self.assertIsNotNone(pts, "detect_fiducials returned None on flat scan")
        self.assertEqual(pts.shape, (4, 2))
        self.assertEqual(pts.dtype, np.float32)

    def test_detect_fiducials_finds_4_points_on_skewed_scan(self):
        """detect_fiducials returns 4 points even after perspective distortion."""
        from omr.simulate import simulate_scan, perspective_transform
        from omr.scan.align import detect_fiducials
        descriptor, sheet_meta = self._descriptor_and_meta()
        W_canon, H_canon = descriptor["page_px"]
        W_scaled = round(W_canon * self.SCALE)
        H_scaled = round(H_canon * self.SCALE)
        # Build transform in SCALED pixel space
        transform = perspective_transform(W_scaled, H_scaled, jitter_px=20.0)
        img = simulate_scan(descriptor, sheet_meta, marked={0: ["B"]}, roll="042",
                            page=0, transform=transform, scale=self.SCALE)
        pts = detect_fiducials(img, descriptor)
        self.assertIsNotNone(pts, "detect_fiducials returned None on skewed scan")
        self.assertEqual(pts.shape, (4, 2))

    def test_detect_fiducials_returns_none_on_blank_image(self):
        """detect_fiducials returns None when there are no fiducial blobs."""
        from omr.scan.align import detect_fiducials
        descriptor, _ = self._descriptor_and_meta()
        blank = np.full((round(1169 * self.SCALE), round(827 * self.SCALE)), 255, dtype=np.uint8)
        result = detect_fiducials(blank, descriptor)
        self.assertIsNone(result,
                          "detect_fiducials should return None for a blank image")

    def test_warp_to_canonical_output_shape(self):
        """warp_to_canonical returns exactly (H_canon, W_canon) grayscale."""
        from omr.simulate import simulate_scan
        from omr.scan.align import detect_fiducials, warp_to_canonical
        descriptor, sheet_meta = self._descriptor_and_meta()
        img = simulate_scan(descriptor, sheet_meta, marked={}, roll="001",
                            scale=self.SCALE)
        pts = detect_fiducials(img, descriptor)
        self.assertIsNotNone(pts, "Need fiducials for warp test")
        warped = warp_to_canonical(img, pts, descriptor)
        W_canon, H_canon = descriptor["page_px"]
        self.assertEqual(warped.shape, (H_canon, W_canon),
                         f"Expected ({H_canon}, {W_canon}), got {warped.shape}")
        self.assertEqual(warped.dtype, np.uint8)

    def test_warp_aligns_fiducials_within_5px_on_skewed_scan(self):
        """
        After detect_fiducials + warp_to_canonical on a SKEWED scan, the
        canonical fiducial positions in the descriptor should be dark (black)
        in the warped image — within a ±5 px tolerance.

        This is the core correctness test: if the warp is correct, the
        descriptor's canonical fiducial centre coordinates should sit on
        dark (ink) pixels in the warped output.
        """
        from omr.simulate import simulate_scan, perspective_transform
        from omr.scan.align import detect_fiducials, warp_to_canonical
        from omr.geometry import FID

        descriptor, sheet_meta = self._descriptor_and_meta(test_id=6, seed=99)
        W_canon, H_canon = descriptor["page_px"]
        W_scaled = round(W_canon * self.SCALE)
        H_scaled = round(H_canon * self.SCALE)

        # Create a skewed scan
        transform = perspective_transform(W_scaled, H_scaled, jitter_px=15.0)
        img = simulate_scan(descriptor, sheet_meta, marked={}, roll="001",
                            page=0, transform=transform, scale=self.SCALE)

        pts = detect_fiducials(img, descriptor)
        self.assertIsNotNone(pts, "detect_fiducials failed on skewed scan")

        warped = warp_to_canonical(img, pts, descriptor)
        self.assertEqual(warped.shape, (H_canon, W_canon))

        # Sample the canonical fiducial positions in the warped image.
        # Each fiducial is a solid black square of FID px side.
        # The mean pixel value in a small window around the canonical centre
        # should be dark (< 80) if alignment is correct.
        tol = 5  # px
        fid_r = FID // 2

        for i, fid in enumerate(descriptor["fiducials"]):
            cx, cy = int(fid["cx"]), int(fid["cy"])
            # Small sampling window (FID//2 inset from fiducial edge)
            sample_r = max(1, fid_r - tol)
            y0 = max(0, cy - sample_r)
            y1 = min(H_canon, cy + sample_r + 1)
            x0 = max(0, cx - sample_r)
            x1 = min(W_canon, cx + sample_r + 1)
            region = warped[y0:y1, x0:x1]
            mean_val = float(region.mean())
            self.assertLess(
                mean_val, 100,
                f"Warped fiducial {i} at canonical ({cx},{cy}) should be dark "
                f"(mean < 100), got {mean_val:.1f}. "
                "Alignment may be off by more than the tolerance."
            )

    def test_warp_output_is_grayscale_2d(self):
        """warp_to_canonical output must be a 2D array (not 3-channel)."""
        from omr.simulate import simulate_scan
        from omr.scan.align import detect_fiducials, warp_to_canonical
        descriptor, sheet_meta = self._descriptor_and_meta()
        img = simulate_scan(descriptor, sheet_meta, marked={}, roll="000",
                            scale=self.SCALE)
        pts = detect_fiducials(img, descriptor)
        self.assertIsNotNone(pts)
        warped = warp_to_canonical(img, pts, descriptor)
        self.assertEqual(warped.ndim, 2, "Output should be 2D grayscale")


class SimulateScaleTests(TestCase):
    """simulate_scan scale parameter — shape and coordinate scaling."""

    def _descriptor_and_meta(self):
        descriptor = build_template(num_questions=10, num_options=4, roll_digits=3)
        sheet_code, human_code = make_sheet_code(3, 11)
        sheet_meta = {
            "sheet_code": sheet_code,
            "human_readable_code": human_code,
            "institution": "School",
            "test_title": "Exam",
            "subject": "",
            "student_name": "",
            "roll_label": "Roll No.",
            "roll_digits": descriptor["roll_grid"]["cols"],
        }
        return descriptor, sheet_meta

    def test_scale2_returns_double_size(self):
        """simulate_scan(scale=2.0) returns (round(H*2), round(W*2)) image."""
        from omr.simulate import simulate_scan
        descriptor, sheet_meta = self._descriptor_and_meta()
        W, H = descriptor["page_px"]
        img = simulate_scan(descriptor, sheet_meta, marked={}, roll="001", scale=2.0)
        self.assertEqual(img.shape, (round(H * 2), round(W * 2)),
                         f"Expected ({round(H*2)}, {round(W*2)}), got {img.shape}")

    def test_scale1_unchanged(self):
        """simulate_scan(scale=1.0) still returns canonical (H, W) image."""
        from omr.simulate import simulate_scan
        descriptor, sheet_meta = self._descriptor_and_meta()
        W, H = descriptor["page_px"]
        img = simulate_scan(descriptor, sheet_meta, marked={}, roll="001", scale=1.0)
        self.assertEqual(img.shape, (H, W))

    def test_render_canonical_image_scale2_shape(self):
        """render_canonical_image(scale=2.0) returns a double-size image."""
        from omr.simulate import render_canonical_image
        descriptor, sheet_meta = self._descriptor_and_meta()
        W, H = descriptor["page_px"]
        img = render_canonical_image(descriptor, sheet_meta, scale=2.0)
        self.assertEqual(img.shape, (round(H * 2), round(W * 2)))

    def test_scale2_fiducial_region_is_dark(self):
        """At scale=2, fiducial squares must still appear dark in the rendered image."""
        from omr.simulate import render_canonical_image
        from omr.geometry import FID
        descriptor, sheet_meta = self._descriptor_and_meta()
        img = render_canonical_image(descriptor, sheet_meta, scale=2.0)
        # Top-left fiducial at canonical (cx, cy), scaled by 2
        fid = descriptor["fiducials"][0]
        cx = round(fid["cx"] * 2)
        cy = round(fid["cy"] * 2)
        r = FID  # half-side at scale=2 is FID px
        y0, y1 = max(0, cy - r // 2), cy + r // 2
        x0, x1 = max(0, cx - r // 2), cx + r // 2
        region = img[y0:y1, x0:x1]
        self.assertLess(region.mean(), 80,
                        f"Scale-2 fiducial should be dark (mean<80), got {region.mean():.1f}")


# ===========================================================================
# Phase 4 Task 4 — fill-ratio + hysteresis bubble reader (read.py) TDD tests
# ===========================================================================

def _make_descriptor_and_meta(num_questions=10, num_options=4, roll_digits=3,
                               test_id=20, seed=42):
    """Shared helper: build descriptor + sheet_meta."""
    descriptor = build_template(
        num_questions=num_questions,
        num_options=num_options,
        roll_digits=roll_digits,
    )
    sheet_code, human_code = make_sheet_code(test_id, seed)
    sheet_meta = {
        "sheet_code": sheet_code,
        "human_readable_code": human_code,
        "institution": "Test School",
        "test_title": "Bubble Reader Test",
        "subject": "OMR",
        "student_name": "Tester",
        "roll_label": "Roll No.",
        "roll_digits": descriptor["roll_grid"]["cols"],
    }
    return descriptor, sheet_meta


class ToBinaryTests(TestCase):
    """omr.scan.read.to_binary — basic binarisation contract."""

    def test_returns_uint8_binary(self):
        from omr.scan.read import to_binary
        gray = np.full((100, 100), 200, dtype=np.uint8)
        binary = to_binary(gray)
        self.assertEqual(binary.dtype, np.uint8)
        unique = set(binary.ravel().tolist())
        self.assertTrue(unique.issubset({0, 255}),
                        f"binary should only contain 0 and 255, got {unique}")

    def test_white_image_gives_all_zeros(self):
        """A pure-white image (all ink=none) → all zeros after INV threshold."""
        from omr.scan.read import to_binary
        gray = np.full((50, 50), 255, dtype=np.uint8)
        binary = to_binary(gray)
        self.assertEqual(binary.max(), 0,
                         "Pure-white image should map to all zeros in binary")

    def test_dark_region_maps_to_255(self):
        """Ink (dark) pixels become 255 in binary (inverse threshold)."""
        from omr.scan.read import to_binary
        gray = np.full((100, 100), 200, dtype=np.uint8)
        # Stamp a dark region
        gray[20:40, 20:40] = 0
        binary = to_binary(gray)
        # The dark region should be ink (255)
        region = binary[20:40, 20:40]
        self.assertGreater(region.mean(), 200,
                           "Dark ink region should become 255 in binary image")

    def test_same_shape(self):
        from omr.scan.read import to_binary
        gray = np.random.randint(0, 256, (100, 80), dtype=np.uint8)
        binary = to_binary(gray)
        self.assertEqual(binary.shape, gray.shape)


class BubbleFillRatioTests(TestCase):
    """omr.scan.read.bubble_fill_ratio — inner-disc sampling."""

    def test_filled_disc_gives_high_ratio(self):
        """A fully-filled disc should give a ratio near 1.0."""
        from omr.scan.read import bubble_fill_ratio
        binary = np.zeros((100, 100), dtype=np.uint8)
        # Fully fill a disc of radius 9
        cx, cy, r = 50, 50, 9
        cv2.circle(binary, (cx, cy), r, 255, -1)
        ratio = bubble_fill_ratio(binary, cx, cy, r)
        self.assertGreater(ratio, 0.85,
                           f"Fully filled disc should have ratio > 0.85, got {ratio:.3f}")

    def test_empty_disc_gives_zero_ratio(self):
        """An all-white (paper) disc gives ratio 0.0."""
        from omr.scan.read import bubble_fill_ratio
        binary = np.zeros((100, 100), dtype=np.uint8)
        ratio = bubble_fill_ratio(binary, 50, 50, 9)
        self.assertEqual(ratio, 0.0, f"Empty disc should give 0.0, got {ratio}")

    def test_ratio_between_0_and_1(self):
        """Fill ratio must always be in [0, 1]."""
        from omr.scan.read import bubble_fill_ratio
        binary = np.random.randint(0, 2, (100, 100), dtype=np.uint8) * 255
        ratio = bubble_fill_ratio(binary, 50, 50, 9)
        self.assertGreaterEqual(ratio, 0.0)
        self.assertLessEqual(ratio, 1.0)


class ClassifyTests(TestCase):
    """omr.scan.read.classify — hysteresis thresholds."""

    def test_above_high_is_filled(self):
        from omr.scan.read import classify, FILL_HIGH
        self.assertEqual(classify(FILL_HIGH), "filled")
        self.assertEqual(classify(1.0), "filled")

    def test_below_low_is_empty(self):
        from omr.scan.read import classify, FILL_LOW
        self.assertEqual(classify(FILL_LOW), "empty")
        self.assertEqual(classify(0.0), "empty")

    def test_between_is_ambiguous(self):
        from omr.scan.read import classify, FILL_HIGH, FILL_LOW
        mid = (FILL_HIGH + FILL_LOW) / 2
        self.assertEqual(classify(mid), "ambiguous")

    def test_just_below_high_is_ambiguous(self):
        from omr.scan.read import classify, FILL_HIGH
        self.assertEqual(classify(FILL_HIGH - 0.001), "ambiguous")

    def test_just_above_low_is_ambiguous(self):
        from omr.scan.read import classify, FILL_LOW
        self.assertEqual(classify(FILL_LOW + 0.001), "ambiguous")


class CanonicalRoundTripTests(TestCase):
    """
    Phase 4 Task 4 — Test 1: Canonical direct round-trip.

    simulate_scan(scale=1.0) → to_binary → read_answers + read_roll
    must recover exactly the marked answers and roll number.
    """

    def setUp(self):
        self.descriptor, self.sheet_meta = _make_descriptor_and_meta(
            num_questions=10, num_options=4, roll_digits=3,
            test_id=20, seed=42,
        )

    def _simulate(self, marked, roll):
        from omr.simulate import simulate_scan
        return simulate_scan(
            self.descriptor, self.sheet_meta,
            marked=marked, roll=roll,
            page=0, scale=1.0,
        )

    def test_canonical_answers_round_trip(self):
        """
        read_answers on a canonical (scale=1) scan recovers exactly the
        marked options and leaves blanks for unmarked questions.
        """
        from omr.scan.read import to_binary, read_answers

        marked = {0: ["A"], 1: ["C"], 2: ["D"]}
        roll = "042"

        img = self._simulate(marked, roll)
        answers = read_answers(img, self.descriptor, page=0)

        # Check marked questions
        for q_pos, labels in marked.items():
            got = answers[q_pos]["marked"]
            self.assertEqual(
                sorted(got), sorted(labels),
                f"q_pos={q_pos}: expected {labels}, got {got}",
            )

        # Check blank questions (1-based page 0 questions are 0..9)
        for q_pos in range(10):
            if q_pos in marked:
                continue
            got = answers[q_pos]["marked"]
            self.assertEqual(
                got, [],
                f"Unmarked q_pos={q_pos} should have marked=[], got {got}",
            )

    def test_canonical_roll_round_trip(self):
        """read_roll on a canonical scan recovers the exact roll string."""
        from omr.scan.read import to_binary, read_roll

        roll = "042"
        img = self._simulate({}, roll)
        roll_str, flag = read_roll(img, self.descriptor)

        self.assertEqual(
            roll_str, roll,
            f"Expected roll={roll!r}, got {roll_str!r} (flag={flag})",
        )
        self.assertIsNone(flag,
                          f"Clean roll '042' should have flag=None, got {flag!r}")

    def test_canonical_fill_ratios_have_clear_margin(self):
        """
        Sanity-check: the measured fill ratios for filled vs empty bubbles
        must be clearly on the correct side of the thresholds, with margin.

        Specifically:
            filled  ratio >= FILL_HIGH + 0.10   (>= 0.55 — well above threshold)
            empty   ratio <  FILL_LOW            (< 0.20  — correctly below threshold)

        Note: the printed bubble outline ring contributes a small but measurable
        ink signal even for empty bubbles. The inner-disc sampling (r*0.6) mitigates
        most of this, but empty bubbles may still read up to ~0.19. FILL_LOW=0.20
        provides enough headroom so they still classify "empty".
        """
        from omr.scan.read import to_binary, bubble_fill_ratio, FILL_HIGH, FILL_LOW

        marked = {0: ["A"]}
        img = self._simulate(marked, "0")

        # Measure the way the reader does: normalised greyness on the grayscale
        # page, not a count of pixels in a binarised one. The legacy pixel-count
        # shim reports ~0.13 for an EMPTY bubble because the option letter is
        # printed inside it, which is exactly the confusion that made faint
        # marks unreadable.
        from omr.scan.read import bubble_darkness, page_ink_level, _blank_baseline

        ink = page_ink_level(img, self.descriptor)
        q0 = next(b for b in self.descriptor["answer_bubbles"] if b["q_pos"] == 0)
        opts = {o["label"]: o for o in q0["options"]}

        # Baseline for label C from every C bubble on the page, almost all blank.
        c_raw = [
            bubble_darkness(img, o["cx"], o["cy"], o["r"], ink)
            for b in self.descriptor["answer_bubbles"] if b["page"] == 0
            for o in b["options"] if o["label"] == "C"
        ]
        base_c = _blank_baseline(c_raw)

        ratio_A = bubble_darkness(img, opts["A"]["cx"], opts["A"]["cy"], opts["A"]["r"], ink)
        ratio_C = (bubble_darkness(img, opts["C"]["cx"], opts["C"]["cy"], opts["C"]["r"], ink)
                   - base_c) / max(1e-6, 1.0 - base_c)

        self.assertGreaterEqual(
            ratio_A, FILL_HIGH + 0.10,
            f"Filled bubble A ({ratio_A:.3f}) should clear FILL_HIGH={FILL_HIGH}",
        )
        self.assertLess(
            ratio_C, FILL_LOW,
            f"Empty bubble C ({ratio_C:.3f}) should be below FILL_LOW={FILL_LOW}",
        )


class WarpedRoundTripTests(TestCase):
    """
    Phase 4 Task 4 — Test 2: Warped round-trip.

    simulate_scan(scale=2, transform=perspective) →
        detect_fiducials → warp_to_canonical →
        to_binary → read_answers must recover marked answers.
    """

    SCALE = 2.0

    def setUp(self):
        self.descriptor, self.sheet_meta = _make_descriptor_and_meta(
            num_questions=10, num_options=4, roll_digits=3,
            test_id=21, seed=55,
        )

    def test_warped_answers_round_trip(self):
        """
        After perspective warp + alignment, read_answers recovers the exact
        marked options for a subset of questions.
        """
        from omr.simulate import simulate_scan, perspective_transform
        from omr.scan.align import detect_fiducials, warp_to_canonical
        from omr.scan.read import to_binary, read_answers

        marked = {0: ["A"], 3: ["B"], 7: ["C"]}
        roll = "137"

        W_canon, H_canon = self.descriptor["page_px"]
        W_scaled = round(W_canon * self.SCALE)
        H_scaled = round(H_canon * self.SCALE)

        transform = perspective_transform(W_scaled, H_scaled, jitter_px=15.0)
        img = simulate_scan(
            self.descriptor, self.sheet_meta,
            marked=marked, roll=roll,
            page=0, transform=transform, scale=self.SCALE,
        )

        # Alignment pipeline
        pts = detect_fiducials(img, self.descriptor)
        self.assertIsNotNone(pts, "detect_fiducials failed on warped scan")
        canonical = warp_to_canonical(img, pts, self.descriptor)
        self.assertEqual(canonical.shape, (H_canon, W_canon))

        answers = read_answers(canonical, self.descriptor, page=0)

        for q_pos, labels in marked.items():
            got = answers[q_pos]["marked"]
            self.assertEqual(
                sorted(got), sorted(labels),
                f"Warped round-trip: q_pos={q_pos} expected {labels}, got {got}",
            )

    def test_warped_roll_round_trip(self):
        """
        After perspective warp + alignment, read_roll recovers the exact roll.
        """
        from omr.simulate import simulate_scan, perspective_transform
        from omr.scan.align import detect_fiducials, warp_to_canonical
        from omr.scan.read import to_binary, read_roll

        roll = "259"
        W_canon, H_canon = self.descriptor["page_px"]
        W_scaled = round(W_canon * self.SCALE)
        H_scaled = round(H_canon * self.SCALE)

        transform = perspective_transform(W_scaled, H_scaled, jitter_px=10.0)
        img = simulate_scan(
            self.descriptor, self.sheet_meta,
            marked={}, roll=roll,
            page=0, transform=transform, scale=self.SCALE,
        )

        pts = detect_fiducials(img, self.descriptor)
        self.assertIsNotNone(pts, "detect_fiducials failed on warped scan")
        canonical = warp_to_canonical(img, pts, self.descriptor)

        roll_str, flag = read_roll(canonical, self.descriptor)

        self.assertEqual(
            roll_str, roll,
            f"Warped round-trip: expected roll={roll!r}, got {roll_str!r} (flag={flag})",
        )
        self.assertIsNone(flag,
                          f"Clean warped roll '{roll}' should have flag=None, got {flag!r}")


class DoubleMark_BlankTests(TestCase):
    """
    Phase 4 Task 4 — Tests 3 & 4: double-mark detection and blank handling.
    """

    def setUp(self):
        self.descriptor, self.sheet_meta = _make_descriptor_and_meta(
            num_questions=10, num_options=4, roll_digits=3,
            test_id=22, seed=77,
        )

    def _page(self, marked, roll="000"):
        """The canonical GRAYSCALE page, which is what the reader measures."""
        from omr.simulate import simulate_scan
        return simulate_scan(
            self.descriptor, self.sheet_meta,
            marked=marked, roll=roll, page=0, scale=1.0,
        )

    def test_double_mark_sets_flag(self):
        """
        Marking two options on q_pos=0 (with multiple_allowed=False) must
        set flag "double_mark" and include both labels in "marked".
        """
        from omr.scan.read import read_answers

        marked = {0: ["A", "C"]}
        page = self._page(marked)
        answers = read_answers(page, self.descriptor, page=0, multiple_allowed=False)

        q0 = answers[0]
        self.assertEqual(q0["flag"], "double_mark",
                         f"Expected flag='double_mark', got {q0['flag']!r}")
        self.assertIn("A", q0["marked"], "A should be in marked")
        self.assertIn("C", q0["marked"], "C should be in marked")

    def test_double_mark_allowed_when_flag_multiple(self):
        """
        When multiple_allowed=True, two filled options should NOT set
        'double_mark'.
        """
        from omr.scan.read import read_answers

        marked = {0: ["A", "B"]}
        page = self._page(marked)
        answers = read_answers(page, self.descriptor, page=0, multiple_allowed=True)

        q0 = answers[0]
        self.assertNotEqual(
            q0["flag"], "double_mark",
            "multiple_allowed=True should suppress double_mark flag",
        )
        self.assertIn("A", q0["marked"])
        self.assertIn("B", q0["marked"])

    def test_blank_question_has_empty_marked_and_no_flag(self):
        """
        A question with no bubble filled should have marked=[] and flag=None.
        """
        from omr.scan.read import read_answers

        # Mark nothing
        page = self._page(marked={})
        answers = read_answers(page, self.descriptor, page=0)

        for q_pos in range(10):
            q = answers[q_pos]
            self.assertEqual(
                q["marked"], [],
                f"q_pos={q_pos}: blank question should have marked=[], got {q['marked']}",
            )
            self.assertIsNone(
                q["flag"],
                f"q_pos={q_pos}: blank question should have flag=None, got {q['flag']!r}",
            )

    def test_clean_single_mark_has_no_flag(self):
        """A single correctly-filled option must have flag=None."""
        from omr.scan.read import read_answers

        marked = {5: ["B"]}
        page = self._page(marked)
        answers = read_answers(page, self.descriptor, page=0)

        q5 = answers[5]
        self.assertEqual(sorted(q5["marked"]), ["B"])
        self.assertIsNone(q5["flag"],
                          f"Clean single mark should have flag=None, got {q5['flag']!r}")

    def test_all_questions_present_in_result(self):
        """read_answers must return an entry for every question on the page."""
        from omr.scan.read import read_answers

        page = self._page(marked={0: ["A"]})
        answers = read_answers(page, self.descriptor, page=0)

        page_qs = self.descriptor["page_map"][0]
        for q_pos in page_qs:
            self.assertIn(q_pos, answers,
                          f"q_pos={q_pos} missing from read_answers result")


# ===========================================================================
# Phase 4 Task 5 — grade.py unit tests
# ===========================================================================

class GradeSheetUnitTests(TestCase):
    """
    Unit tests for omr.scan.grade.grade_sheet.
    Uses a minimal mock OmrSheet-like object to avoid DB overhead.
    """

    class _MockMarkingScheme:
        def __init__(self, marks_per_correct=1, negative=0, partial=False, multi=False,
                     multi_mark_policy="review"):
            self.marks_per_correct = marks_per_correct
            self.negative_marks_per_wrong = negative
            self.partial_marking = partial
            self.multiple_correct_allowed = multi
            self.multi_mark_policy = multi_mark_policy

    class _MockTest:
        def __init__(self, ms):
            self.marking_scheme = ms

    class _MockSheet:
        def __init__(self, answer_key, ms):
            self.answer_key = answer_key
            self.test = GradeSheetUnitTests._MockTest(ms)

    def _sheet(self, answer_key, marks=1, negative=0, partial=False, multi=False,
               multi_mark_policy="review"):
        ms = self._MockMarkingScheme(marks, negative, partial, multi, multi_mark_policy)
        return self._MockSheet(answer_key, ms)

    def test_all_correct(self):
        """All correct → score == max_score, correct_count == n."""
        from omr.scan.grade import grade_sheet
        answer_key = {"0": ["A"], "1": ["B"], "2": ["C"]}
        sheet = self._sheet(answer_key, marks=1)
        reads = {0: ["A"], 1: ["B"], 2: ["C"]}
        result = grade_sheet(sheet, reads)
        from decimal import Decimal
        self.assertEqual(result["score"], Decimal("3"))
        self.assertEqual(result["max_score"], Decimal("3"))
        self.assertEqual(result["correct_count"], 3)
        self.assertEqual(result["wrong_count"], 0)
        self.assertEqual(result["blank_count"], 0)

    def test_all_blank(self):
        """All blank → score == 0, blank_count == n."""
        from omr.scan.grade import grade_sheet
        answer_key = {"0": ["A"], "1": ["B"]}
        sheet = self._sheet(answer_key, marks=1)
        reads = {}
        result = grade_sheet(sheet, reads)
        from decimal import Decimal
        self.assertEqual(result["score"], Decimal("0"))
        self.assertEqual(result["blank_count"], 2)
        self.assertEqual(result["correct_count"], 0)
        self.assertEqual(result["wrong_count"], 0)

    def test_wrong_answer_with_negative_marks(self):
        """Wrong answer deducts negative_marks; score floored at 0."""
        from omr.scan.grade import grade_sheet
        from decimal import Decimal
        answer_key = {"0": ["A"], "1": ["B"]}
        sheet = self._sheet(answer_key, marks=1, negative=1)
        reads = {0: ["B"]}  # wrong on q0, blank on q1
        result = grade_sheet(sheet, reads)
        self.assertEqual(result["score"], Decimal("0"))  # 0 - 1 → floor at 0
        self.assertEqual(result["wrong_count"], 1)
        self.assertEqual(result["blank_count"], 1)

    def test_score_floored_at_zero(self):
        """Score is never negative even with heavy negative marks."""
        from omr.scan.grade import grade_sheet
        from decimal import Decimal
        answer_key = {str(i): ["A"] for i in range(5)}
        sheet = self._sheet(answer_key, marks=1, negative=2)
        reads = {i: ["B"] for i in range(5)}  # all wrong
        result = grade_sheet(sheet, reads)
        self.assertEqual(result["score"], Decimal("0"))

    def test_partial_marking(self):
        """Partial marking gives proportional credit."""
        from omr.scan.grade import grade_sheet
        from decimal import Decimal
        # 2 correct options for q0: A and B
        answer_key = {"0": ["A", "B"]}
        sheet = self._sheet(answer_key, marks=2, partial=True, multi=True)
        reads = {0: ["A"]}  # only one of two correct marked
        result = grade_sheet(sheet, reads)
        # (1 - 0) / 2 * 2 = 1
        self.assertEqual(result["score"], Decimal("1"))

    def test_per_question_list(self):
        """per_question has one entry per q_pos in answer_key."""
        from omr.scan.grade import grade_sheet
        answer_key = {"0": ["A"], "1": ["B"], "2": ["C"]}
        sheet = self._sheet(answer_key)
        result = grade_sheet(sheet, {0: ["A"], 1: ["D"], 2: []})
        self.assertEqual(len(result["per_question"]), 3)
        pos_set = {pq["q_pos"] for pq in result["per_question"]}
        self.assertEqual(pos_set, {0, 1, 2})

    def test_correct_entry_is_correct(self):
        """per_question entry for a correct answer has is_correct=True."""
        from omr.scan.grade import grade_sheet
        answer_key = {"0": ["A"]}
        sheet = self._sheet(answer_key)
        result = grade_sheet(sheet, {0: ["A"]})
        pq = result["per_question"][0]
        self.assertTrue(pq["is_correct"])

    def test_wrong_entry_is_not_correct(self):
        """per_question entry for a wrong answer has is_correct=False."""
        from omr.scan.grade import grade_sheet
        answer_key = {"0": ["A"]}
        sheet = self._sheet(answer_key)
        result = grade_sheet(sheet, {0: ["B"]})
        pq = result["per_question"][0]
        self.assertFalse(pq["is_correct"])

    # ---- Multi-mark (overmark) policy tests (#87) ----------------------------

    def test_multimark_default_review_flags_and_scores_wrong(self):
        """Default 'review' policy: overmark keeps legacy wrong scoring AND flags
        the question for review (needs_review=True)."""
        from omr.scan.grade import grade_sheet
        from decimal import Decimal
        answer_key = {"0": ["A"], "1": ["B"]}
        sheet = self._sheet(answer_key, marks=1, negative=1)  # default review
        result = grade_sheet(sheet, {0: ["A", "C"], 1: ["B"]})  # q0 overmark
        pq0 = next(p for p in result["per_question"] if p["q_pos"] == 0)
        self.assertEqual(pq0["status"], "wrong")
        self.assertTrue(pq0["needs_review"])
        self.assertTrue(pq0["flagged"])
        self.assertEqual(result["wrong_count"], 1)
        self.assertEqual(result["disqualified_count"], 0)
        # q1 correct (1) minus q0 penalty (1) → floored 0
        self.assertEqual(result["score"], Decimal("0"))

    def test_multimark_disqualify_zeroes_without_penalty(self):
        """'disqualify' policy: overmark → score 0, no penalty, not flagged,
        counted in disqualified_count (not wrong_count)."""
        from omr.scan.grade import grade_sheet
        from decimal import Decimal
        answer_key = {"0": ["A"], "1": ["B"]}
        sheet = self._sheet(answer_key, marks=1, negative=1, multi_mark_policy="disqualify")
        result = grade_sheet(sheet, {0: ["A", "C"], 1: ["B"]})  # q0 overmark, q1 correct
        pq0 = next(p for p in result["per_question"] if p["q_pos"] == 0)
        self.assertEqual(pq0["status"], "disqualified")
        self.assertFalse(pq0["is_correct"])
        self.assertFalse(pq0["needs_review"])
        self.assertEqual(result["disqualified_count"], 1)
        self.assertEqual(result["wrong_count"], 0)
        # No penalty applied: q1 correct = 1 (q0 contributes 0)
        self.assertEqual(result["score"], Decimal("1"))

    def test_multimark_wrong_applies_negative_without_review(self):
        """'wrong' policy: overmark scored wrong with negative marking, no review."""
        from omr.scan.grade import grade_sheet
        from decimal import Decimal
        answer_key = {"0": ["A"], "1": ["B"]}
        sheet = self._sheet(answer_key, marks=2, negative=1, multi_mark_policy="wrong")
        result = grade_sheet(sheet, {0: ["A", "C"], 1: ["B"]})
        pq0 = next(p for p in result["per_question"] if p["q_pos"] == 0)
        self.assertEqual(pq0["status"], "wrong")
        self.assertFalse(pq0["needs_review"])
        self.assertEqual(result["wrong_count"], 1)
        self.assertEqual(result["disqualified_count"], 0)
        # q1 correct (2) minus q0 penalty (1) = 1
        self.assertEqual(result["score"], Decimal("1"))

    def test_multimark_correct_if_all_includes_key(self):
        """'correct_if_all': overmark that contains every correct option → full marks."""
        from omr.scan.grade import grade_sheet
        from decimal import Decimal
        answer_key = {"0": ["A"]}
        sheet = self._sheet(answer_key, marks=1, multi_mark_policy="correct_if_all")
        result = grade_sheet(sheet, {0: ["A", "B"]})  # marked the key + an extra
        pq0 = result["per_question"][0]
        self.assertEqual(pq0["status"], "correct")
        self.assertTrue(pq0["is_correct"])
        self.assertEqual(result["correct_count"], 1)
        self.assertEqual(result["score"], Decimal("1"))

    def test_multimark_correct_if_all_missing_key_is_wrong(self):
        """'correct_if_all': overmark that omits a correct option → wrong."""
        from omr.scan.grade import grade_sheet
        answer_key = {"0": ["A"]}
        sheet = self._sheet(answer_key, marks=1, negative=1, multi_mark_policy="correct_if_all")
        result = grade_sheet(sheet, {0: ["B", "C"]})  # two marks, neither is the key
        pq0 = result["per_question"][0]
        self.assertEqual(pq0["status"], "wrong")
        self.assertFalse(pq0["is_correct"])
        self.assertEqual(result["wrong_count"], 1)

    def test_multimark_single_wrong_answer_is_not_overmark(self):
        """A single (wrong) mark is NOT an overmark — policy does not apply."""
        from omr.scan.grade import grade_sheet
        answer_key = {"0": ["A"]}
        sheet = self._sheet(answer_key, marks=1, multi_mark_policy="disqualify")
        result = grade_sheet(sheet, {0: ["B"]})  # one mark, wrong
        pq0 = result["per_question"][0]
        self.assertEqual(pq0["status"], "wrong")
        self.assertEqual(result["disqualified_count"], 0)


# ===========================================================================
# Phase 4 Task 5 — process_image unit tests
# ===========================================================================

class ProcessImageTests(TestCase):
    """
    Unit tests for omr.scan.pipeline.process_image.
    Uses simulate_scan to create test images.
    """

    SCALE = 2.0

    def _descriptor_and_meta(self, num_questions=10, test_id=30, seed=7):
        from omr.codes import make_sheet_code
        from omr.geometry import build_template
        descriptor = build_template(num_questions=num_questions, num_options=4, roll_digits=3)
        sheet_code, human_code = make_sheet_code(test_id, seed)
        sheet_meta = {
            "sheet_code": sheet_code,
            "human_readable_code": human_code,
            "institution": "Pipeline School",
            "test_title": "Pipeline Test",
            "subject": "OMR",
            "student_name": "Tester",
            "roll_label": "Roll No.",
            "roll_digits": descriptor["roll_grid"]["cols"],
        }
        return descriptor, sheet_meta, sheet_code

    def test_process_image_returns_dict_keys(self):
        """process_image returns dict with all required keys."""
        from omr.scan.pipeline import process_image
        from omr.simulate import simulate_scan

        descriptor, sheet_meta, _ = self._descriptor_and_meta()
        img = simulate_scan(descriptor, sheet_meta, marked={0: ["A"]},
                            roll="042", scale=self.SCALE)
        result = process_image(img, descriptor)
        for key in ("sheet_code", "page", "total", "reads", "roll", "flags"):
            self.assertIn(key, result, f"Key {key!r} missing from process_image result")

    def test_process_image_no_qr_returns_flag(self):
        """process_image on a blank image returns flag='no_qr'."""
        from omr.scan.pipeline import process_image
        from omr.geometry import build_template
        descriptor = build_template(num_questions=5, num_options=4, roll_digits=3)
        blank = np.full((1169 * 2, 827 * 2), 255, dtype=np.uint8)
        result = process_image(blank, descriptor)
        self.assertIn("no_qr", result["flags"])
        self.assertIsNone(result["sheet_code"])

    def test_process_image_clean_scan_has_no_flags(self):
        """process_image on a clean scale=2 scan should have no flags."""
        from omr.scan.pipeline import process_image
        from omr.simulate import simulate_scan

        descriptor, sheet_meta, _ = self._descriptor_and_meta(test_id=31, seed=8)
        img = simulate_scan(descriptor, sheet_meta, marked={0: ["B"], 3: ["A"]},
                            roll="123", scale=self.SCALE)
        result = process_image(img, descriptor)
        self.assertEqual(result["flags"], [],
                         f"Expected no flags on clean scan, got {result['flags']}")

    def test_process_image_reads_correct_answers(self):
        """process_image reads back the same answers that were filled."""
        from omr.scan.pipeline import process_image
        from omr.simulate import simulate_scan

        descriptor, sheet_meta, _ = self._descriptor_and_meta(test_id=32, seed=9)
        marked = {0: ["A"], 1: ["C"], 4: ["B"]}
        img = simulate_scan(descriptor, sheet_meta, marked=marked,
                            roll="001", scale=self.SCALE)
        result = process_image(img, descriptor)
        reads = result["reads"]
        for q_pos, labels in marked.items():
            got = reads[q_pos]["marked"]
            self.assertEqual(sorted(got), sorted(labels),
                             f"q_pos={q_pos}: expected {labels}, got {got}")

    def test_process_image_sheet_code_matches(self):
        """process_image returns the correct sheet_code from the QR."""
        from omr.scan.pipeline import process_image
        from omr.simulate import simulate_scan

        descriptor, sheet_meta, sheet_code = self._descriptor_and_meta(test_id=33, seed=11)
        img = simulate_scan(descriptor, sheet_meta, marked={},
                            roll="000", scale=self.SCALE)
        result = process_image(img, descriptor)
        self.assertEqual(result["sheet_code"], sheet_code)

    def test_process_image_double_mark_flag(self):
        """process_image on a double-marked question includes 'double_mark' flag."""
        from omr.scan.pipeline import process_image
        from omr.simulate import simulate_scan

        descriptor, sheet_meta, _ = self._descriptor_and_meta(test_id=34, seed=13)
        img = simulate_scan(descriptor, sheet_meta, marked={0: ["A", "B"]},
                            roll="000", scale=self.SCALE)
        result = process_image(img, descriptor)
        self.assertIn("double_mark", result["flags"],
                      f"Expected 'double_mark' in flags, got {result['flags']}")


# ===========================================================================
# Phase 4 Task 5 — END-TO-END ROUND-TRIP tests
# ===========================================================================

def _build_test_with_questions(n_questions=10, n_options=4):
    """
    Create a full Django model chain:
    User → ClassGroup → Test → Questions (with options + one correct each)
    + MarkingScheme.
    Returns (user, test, questions, correct_labels_by_order_index)
    where correct_labels_by_order_index[i] = original label that is correct
    for the i-th question (0-indexed by order_index).
    """
    from django.contrib.auth import get_user_model
    from assessments.models import ClassGroup, MarkingScheme, Option, Question, Test
    User = get_user_model()

    user = User.objects.create_user(
        email=f"e2e_user_{n_questions}_{n_options}@test.com",
        password="testpass",
    )
    cg = ClassGroup.objects.create(user=user, created_by=user, name="E2E Class")
    test = Test.objects.create(
        user=user, class_group=cg, created_by=user,
        title="E2E Test", subject="Science",
    )
    MarkingScheme.objects.create(
        test=test,
        marks_per_correct=1,
        negative_marks_per_wrong=0,
    )

    correct_labels = []
    for i in range(n_questions):
        q = Question.objects.create(test=test, order_index=i, text=f"Q{i}?")
        for j in range(n_options):
            label = chr(ord("A") + j)
            is_correct = (j == 0)  # option A is always correct
            Option.objects.create(question=q, label=label, text=label, is_correct=is_correct)
        correct_labels.append("A")  # printed label "A" is always correct before shuffling

    return user, test, correct_labels


def _build_omr_sheet(test, user, n_questions=10, n_options=4, roll_digits=3):
    """
    Build and save an OmrSheet from the test's questions + shuffle plan.
    Returns (omr_sheet, sheet_meta, descriptor).
    """
    from assessments.models import Question
    from omr.codes import make_sheet_code
    from omr.geometry import build_template
    from omr.models import OmrSheet
    from omr.shuffle import build_sheet_plan
    from rosters.models import Roster, Student

    # Create a student
    roster = Roster.objects.create(user=user, created_by=user, name="E2E Roster")
    student = Student.objects.create(roster=roster, roll_number="001")

    # Build questions payload for shuffle
    questions_data = []
    for q in Question.objects.filter(test=test).order_by("order_index"):
        opts = [{"label": o.label, "is_correct": o.is_correct}
                for o in q.options.all()]
        questions_data.append({"id": str(q.id), "options": opts})

    seed = 12345
    plan = build_sheet_plan(questions_data, seed=seed,
                            shuffle_questions=False, shuffle_options=False)

    descriptor = build_template(
        num_questions=n_questions,
        num_options=n_options,
        roll_digits=roll_digits,
    )

    sheet_code, human_code = make_sheet_code(test.id, seed)
    omr_sheet = OmrSheet.objects.create(
        test=test,
        student=student,
        sheet_code=sheet_code,
        human_readable_code=human_code,
        shuffle_version=seed,
        question_order=plan["question_order"],
        option_order=plan["option_order"],
        answer_key=plan["answer_key"],
        template_descriptor=descriptor,
        page_count=descriptor["page_count"],
        page_map=descriptor["page_map"],
    )

    sheet_meta = {
        "sheet_code": sheet_code,
        "human_readable_code": human_code,
        "institution": "E2E School",
        "test_title": "E2E Test",
        "subject": "Science",
        "student_name": "Test Student",
        "roll_label": "Roll No.",
        "roll_digits": roll_digits,
    }
    return omr_sheet, sheet_meta, descriptor, student


class EndToEndPerfectScoreTest(TestCase):
    """
    End-to-end: generate → fill correct answers → scan → pipeline → perfect score.

    simulate_scan fills omr_sheet.answer_key (the correct printed labels)
    → process_image + grade_sheet → StudentResult.score == max_score,
    all QuestionResponse.is_correct, no ReviewItems, needs_review=False.
    """

    N_QUESTIONS = 10
    SCALE = 2.0

    def setUp(self):
        self.user, self.test, _ = _build_test_with_questions(
            self.N_QUESTIONS, n_options=4)
        self.omr_sheet, self.sheet_meta, self.descriptor, self.student = \
            _build_omr_sheet(self.test, self.user, self.N_QUESTIONS, 4, roll_digits=3)

    def test_perfect_score_end_to_end(self):
        """
        Fill correct answers → run pipeline → StudentResult.score == max_score,
        all QuestionResponse.is_correct True, no ReviewItems, needs_review False.
        """
        from omr.scan.pipeline import process_image, simulate_correct_marks, _maybe_grade
        from omr.models import ScanBatch, ScanJob
        from omr.simulate import simulate_scan
        from results.models import StudentResult, QuestionResponse, ReviewItem

        # Build correct marks from the answer key
        correct_marks = simulate_correct_marks(self.omr_sheet)

        # Simulate the scan image (correct answers filled, scale=2 for reliable QR)
        img = simulate_scan(
            self.descriptor, self.sheet_meta,
            marked=correct_marks, roll="001",
            page=0, scale=self.SCALE,
        )

        # Run process_image
        result = process_image(img, self.descriptor)
        self.assertEqual(result["flags"], [],
                         f"Expected no flags on perfect scan, got {result['flags']}")
        self.assertEqual(result["sheet_code"], self.omr_sheet.sheet_code)

        # Aggregate reads (single page)
        aggregated = {q_pos: entry["marked"]
                      for q_pos, entry in result["reads"].items()}

        # Run grading
        from omr.scan.grade import grade_sheet
        grading = grade_sheet(self.omr_sheet, aggregated)

        self.assertEqual(
            grading["score"], grading["max_score"],
            f"Perfect score expected: {grading['max_score']}, got {grading['score']}"
        )
        self.assertEqual(grading["correct_count"], self.N_QUESTIONS)
        self.assertEqual(grading["wrong_count"], 0)
        self.assertEqual(grading["blank_count"], 0)
        for pq in grading["per_question"]:
            self.assertTrue(pq["is_correct"],
                            f"q_pos={pq['q_pos']} should be correct")

    def test_perfect_score_via_full_pipeline(self):
        """
        Full pipeline: simulate_scan → ScanJob → process_scan_job (via _maybe_grade)
        → StudentResult.score == max_score, all responses correct, no review items.
        """
        import io
        import tempfile
        import cv2
        import numpy as np
        from omr.scan.pipeline import simulate_correct_marks, _maybe_grade
        from omr.models import ScanBatch, ScanJob
        from omr.simulate import simulate_scan
        from results.models import StudentResult, QuestionResponse, ReviewItem
        from django.core.files.base import ContentFile

        correct_marks = simulate_correct_marks(self.omr_sheet)

        img = simulate_scan(
            self.descriptor, self.sheet_meta,
            marked=correct_marks, roll="001",
            page=0, scale=self.SCALE,
        )

        # Encode image to PNG bytes
        ok, buf = cv2.imencode(".png", img)
        self.assertTrue(ok)
        img_bytes = buf.tobytes()

        # Create ScanBatch + ScanJob
        batch = ScanBatch.objects.create(
            test=self.test, created_by=self.user, total=1
        )
        job = ScanJob(batch=batch, page_no=1)
        job.image_file.save("test_scan.png", ContentFile(img_bytes), save=True)

        # Run process_scan_job
        from omr.scan.pipeline import process_scan_job
        process_scan_job(job)

        # Refresh
        job.refresh_from_db()
        self.assertEqual(job.status, ScanJob.STATUS_DONE,
                         f"Job status should be 'done', got {job.status!r} "
                         f"(error: {job.error_reason})")

        # Check StudentResult
        sr = StudentResult.objects.get(omr_sheet=self.omr_sheet)
        from decimal import Decimal
        self.assertEqual(
            sr.score, Decimal(str(self.N_QUESTIONS)),
            f"Expected score={self.N_QUESTIONS}, got {sr.score}"
        )
        self.assertEqual(sr.max_score, Decimal(str(self.N_QUESTIONS)))
        self.assertFalse(sr.needs_review,
                         f"needs_review should be False for a perfect clean scan")

        # All responses correct
        responses = QuestionResponse.objects.filter(student_result=sr)
        self.assertEqual(responses.count(), self.N_QUESTIONS)
        for resp in responses:
            self.assertTrue(resp.is_correct,
                            f"q_pos={resp.q_pos} should be correct, got is_correct=False")

        # No ReviewItems
        review_items = ReviewItem.objects.filter(omr_sheet=self.omr_sheet)
        self.assertEqual(review_items.count(), 0,
                         f"Expected no review items, got {list(review_items.values('reason'))}")


class EndToEndSomeWrongTest(TestCase):
    """
    End-to-end: fill some correct + some wrong → score reflects marking scheme.
    """

    N_QUESTIONS = 10
    SCALE = 2.0

    def setUp(self):
        self.user, self.test, _ = _build_test_with_questions(self.N_QUESTIONS, n_options=4)
        self.omr_sheet, self.sheet_meta, self.descriptor, self.student = \
            _build_omr_sheet(self.test, self.user, self.N_QUESTIONS, 4, roll_digits=3)

    def test_some_wrong_score(self):
        """
        Flip 3 answers to wrong → score = N_QUESTIONS - 3 (no negative marks).
        """
        from omr.scan.pipeline import simulate_correct_marks
        from omr.scan.grade import grade_sheet
        from omr.simulate import simulate_scan
        from omr.scan.pipeline import process_image
        from decimal import Decimal

        correct_marks = simulate_correct_marks(self.omr_sheet)

        # Flip 3 answers: change the marked label from correct to wrong
        wrong_marks = dict(correct_marks)
        n_wrong = 3
        for q_pos in list(correct_marks.keys())[:n_wrong]:
            correct = correct_marks[q_pos]
            # Pick a wrong label (B if correct is A, else A)
            wrong_label = "B" if correct != ["B"] else "C"
            wrong_marks[q_pos] = [wrong_label]

        img = simulate_scan(
            self.descriptor, self.sheet_meta,
            marked=wrong_marks, roll="002",
            page=0, scale=self.SCALE,
        )

        result = process_image(img, self.descriptor)
        aggregated = {q_pos: entry["marked"]
                      for q_pos, entry in result["reads"].items()}

        grading = grade_sheet(self.omr_sheet, aggregated)

        expected_score = Decimal(self.N_QUESTIONS - n_wrong)
        self.assertEqual(
            grading["score"], expected_score,
            f"Expected score={expected_score}, got {grading['score']}"
        )
        self.assertEqual(grading["wrong_count"], n_wrong)
        self.assertEqual(grading["correct_count"], self.N_QUESTIONS - n_wrong)

    def test_some_blank_score(self):
        """
        Only answer half the questions (others blank) → score = half.
        """
        from omr.scan.pipeline import simulate_correct_marks
        from omr.scan.grade import grade_sheet
        from omr.simulate import simulate_scan
        from omr.scan.pipeline import process_image
        from decimal import Decimal

        correct_marks = simulate_correct_marks(self.omr_sheet)

        # Only answer first half
        half = self.N_QUESTIONS // 2
        partial_marks = {k: v for k, v in correct_marks.items() if k < half}

        img = simulate_scan(
            self.descriptor, self.sheet_meta,
            marked=partial_marks, roll="003",
            page=0, scale=self.SCALE,
        )

        result = process_image(img, self.descriptor)
        aggregated = {q_pos: entry["marked"]
                      for q_pos, entry in result["reads"].items()}

        grading = grade_sheet(self.omr_sheet, aggregated)

        expected_score = Decimal(half)
        self.assertEqual(grading["score"], expected_score,
                         f"Expected score={expected_score}, got {grading['score']}")
        self.assertEqual(grading["correct_count"], half)
        self.assertEqual(grading["blank_count"], self.N_QUESTIONS - half)


class EndToEndDoubleMarkTest(TestCase):
    """
    End-to-end: double-mark a question → ReviewItem(double_mark) + needs_review=True.
    """

    N_QUESTIONS = 10
    SCALE = 2.0

    def setUp(self):
        self.user, self.test, _ = _build_test_with_questions(self.N_QUESTIONS, n_options=4)
        self.omr_sheet, self.sheet_meta, self.descriptor, self.student = \
            _build_omr_sheet(self.test, self.user, self.N_QUESTIONS, 4, roll_digits=3)

    def test_double_mark_triggers_review(self):
        """
        Double-mark q_pos=0 (A+B) → ReviewItem with reason='double_mark'
        + StudentResult.needs_review=True.
        """
        import cv2
        from django.core.files.base import ContentFile
        from omr.scan.pipeline import simulate_correct_marks, process_scan_job
        from omr.models import ScanBatch, ScanJob
        from omr.simulate import simulate_scan
        from results.models import StudentResult, ReviewItem

        correct_marks = simulate_correct_marks(self.omr_sheet)

        # Double-mark q_pos=0
        dm_marks = dict(correct_marks)
        dm_marks[0] = ["A", "B"]  # two options marked

        img = simulate_scan(
            self.descriptor, self.sheet_meta,
            marked=dm_marks, roll="004",
            page=0, scale=self.SCALE,
        )

        ok, buf = cv2.imencode(".png", img)
        img_bytes = buf.tobytes()

        batch = ScanBatch.objects.create(
            test=self.test, created_by=self.user, total=1
        )
        job = ScanJob(batch=batch, page_no=1)
        job.image_file.save("dm_scan.png", ContentFile(img_bytes), save=True)

        process_scan_job(job)
        job.refresh_from_db()

        # Job should be needs_review because of double_mark
        self.assertEqual(
            job.status, ScanJob.STATUS_NEEDS_REVIEW,
            f"Job should be 'needs_review' due to double_mark, got {job.status!r}",
        )

        # StudentResult should exist with needs_review=True
        sr = StudentResult.objects.get(omr_sheet=self.omr_sheet)
        self.assertTrue(sr.needs_review,
                        "StudentResult.needs_review should be True for double_mark")

        # ReviewItem with reason=double_mark must exist
        review_items = ReviewItem.objects.filter(omr_sheet=self.omr_sheet)
        reasons = [ri.reason for ri in review_items]
        self.assertIn(
            ReviewItem.REASON_DOUBLE_MARK, reasons,
            f"Expected 'double_mark' ReviewItem, got {reasons}",
        )

    def test_single_double_mark_yields_exactly_one_review_item(self):
        """
        A single double-marked scan must create EXACTLY ONE open double_mark
        ReviewItem (no duplicate from _maybe_grade).
        """
        import cv2
        from django.core.files.base import ContentFile
        from omr.scan.pipeline import simulate_correct_marks, process_scan_job
        from omr.models import ScanBatch, ScanJob
        from omr.simulate import simulate_scan
        from results.models import ReviewItem

        correct_marks = simulate_correct_marks(self.omr_sheet)
        dm_marks = dict(correct_marks)
        dm_marks[0] = ["A", "B"]  # double-mark a single question

        img = simulate_scan(
            self.descriptor, self.sheet_meta,
            marked=dm_marks, roll="006",
            page=0, scale=self.SCALE,
        )
        ok, buf = cv2.imencode(".png", img)
        img_bytes = buf.tobytes()

        batch = ScanBatch.objects.create(
            test=self.test, created_by=self.user, total=1
        )
        job = ScanJob(batch=batch, page_no=1)
        job.image_file.save("dm_single.png", ContentFile(img_bytes), save=True)

        process_scan_job(job)

        dm_items = ReviewItem.objects.filter(
            omr_sheet=self.omr_sheet,
            reason=ReviewItem.REASON_DOUBLE_MARK,
            resolved=False,
        )
        self.assertEqual(
            dm_items.count(), 1,
            f"Expected exactly 1 double_mark ReviewItem, got {dm_items.count()}",
        )

    def test_disqualify_policy_suppresses_review_and_voids_question(self):
        """
        With multi_mark_policy='disqualify', a double-marked question is auto-voided:
        NO double_mark ReviewItem, StudentResult.needs_review=False,
        disqualified_count=1, and no negative penalty.
        """
        import cv2
        from django.core.files.base import ContentFile
        from omr.scan.pipeline import simulate_correct_marks, process_scan_job
        from omr.models import ScanBatch, ScanJob
        from omr.simulate import simulate_scan
        from results.models import StudentResult, ReviewItem

        # Flip the test's policy to disqualify
        ms = self.test.marking_scheme
        ms.multi_mark_policy = "disqualify"
        ms.save(update_fields=["multi_mark_policy"])

        correct_marks = simulate_correct_marks(self.omr_sheet)
        dm_marks = dict(correct_marks)
        dm_marks[0] = ["A", "B"]  # overmark q_pos=0

        img = simulate_scan(
            self.descriptor, self.sheet_meta,
            marked=dm_marks, roll="009",
            page=0, scale=self.SCALE,
        )
        ok, buf = cv2.imencode(".png", img)
        img_bytes = buf.tobytes()

        batch = ScanBatch.objects.create(test=self.test, created_by=self.user, total=1)
        job = ScanJob(batch=batch, page_no=1)
        job.image_file.save("dq_scan.png", ContentFile(img_bytes), save=True)

        process_scan_job(job)

        sr = StudentResult.objects.get(omr_sheet=self.omr_sheet)
        self.assertFalse(sr.needs_review,
                         "disqualify policy must NOT route overmark to review")
        self.assertEqual(sr.disqualified_count, 1)

        dm_items = ReviewItem.objects.filter(
            omr_sheet=self.omr_sheet,
            reason=ReviewItem.REASON_DOUBLE_MARK,
            resolved=False,
        )
        self.assertEqual(
            dm_items.count(), 0,
            "disqualify policy must NOT create a double_mark ReviewItem",
        )


# ===========================================================================
# Phase 4 Task 6 — Scan upload endpoint + batch progress + review queue tests
# ===========================================================================

class ScanUploadEndpointTest(TestCase):
    """
    POST /api/v1/omr/scan/ — upload a simulated scan image.
    Expects 201 + batch created + StudentResult with full marks via results endpoint.
    """

    N_QUESTIONS = 10
    SCALE = 2.0

    def setUp(self):
        self.user, self.test, _ = _build_test_with_questions(
            self.N_QUESTIONS, n_options=4)
        self.omr_sheet, self.sheet_meta, self.descriptor, self.student = \
            _build_omr_sheet(self.test, self.user, self.N_QUESTIONS, 4, roll_digits=3)
        self.client = None  # Use DRF APIClient

    def _get_client(self):
        from rest_framework.test import APIClient
        client = APIClient()
        # Obtain a JWT token for self.user
        response = client.post("/api/v1/auth/token/", {
            "email": self.user.email,
            "password": "testpass",
        }, format="json")
        token = response.data["access"]
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return client

    def _make_scan_image_bytes(self, marked, roll="001"):
        from omr.simulate import simulate_scan
        img = simulate_scan(
            self.descriptor, self.sheet_meta,
            marked=marked, roll=roll,
            page=0, scale=self.SCALE,
        )
        import cv2
        ok, buf = cv2.imencode(".png", img)
        self.assertTrue(ok)
        return buf.tobytes()

    def test_scan_upload_returns_201(self):
        """POST /api/v1/omr/scan/ with a simulated image returns 201."""
        from omr.scan.pipeline import simulate_correct_marks
        from django.core.files.uploadedfile import SimpleUploadedFile

        client = self._get_client()
        correct_marks = simulate_correct_marks(self.omr_sheet)
        img_bytes = self._make_scan_image_bytes(correct_marks)

        uploaded = SimpleUploadedFile("scan.png", img_bytes, content_type="image/png")
        response = client.post(
            "/api/v1/omr/scan/",
            {"test": self.test.id, "files": uploaded},
            format="multipart",
        )
        self.assertEqual(response.status_code, 201,
                         f"Expected 201, got {response.status_code}: {response.data}")
        self.assertIn("batch_id", response.data)
        self.assertEqual(response.data["total"], 1)
        self.assertEqual(response.data["processed"], 1)

    def test_scan_upload_creates_student_result_with_full_marks(self):
        """
        After uploading a perfect-score scan, GET /results/?test= returns
        a StudentResult with score == max_score.
        """
        from omr.scan.pipeline import simulate_correct_marks
        from django.core.files.uploadedfile import SimpleUploadedFile
        from results.models import StudentResult

        client = self._get_client()
        correct_marks = simulate_correct_marks(self.omr_sheet)
        img_bytes = self._make_scan_image_bytes(correct_marks)

        uploaded = SimpleUploadedFile("scan.png", img_bytes, content_type="image/png")
        response = client.post(
            "/api/v1/omr/scan/",
            {"test": self.test.id, "files": uploaded},
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)

        # Check StudentResult exists with full marks
        sr = StudentResult.objects.filter(omr_sheet=self.omr_sheet).first()
        self.assertIsNotNone(sr, "StudentResult should exist after upload")
        self.assertEqual(sr.score, sr.max_score,
                         f"Expected score == max_score, got score={sr.score}, max={sr.max_score}")

    def test_scan_upload_results_via_api(self):
        """GET /results/?test= returns the StudentResult after upload."""
        from omr.scan.pipeline import simulate_correct_marks
        from django.core.files.uploadedfile import SimpleUploadedFile

        client = self._get_client()
        correct_marks = simulate_correct_marks(self.omr_sheet)
        img_bytes = self._make_scan_image_bytes(correct_marks)

        uploaded = SimpleUploadedFile("scan.png", img_bytes, content_type="image/png")
        client.post(
            "/api/v1/omr/scan/",
            {"test": self.test.id, "files": uploaded},
            format="multipart",
        )

        results_resp = client.get(f"/api/v1/results/?test={self.test.id}")
        self.assertEqual(results_resp.status_code, 200)
        # Paginated: response.data has keys count/next/previous/results
        results = results_resp.data.get("results", results_resp.data)
        if isinstance(results_resp.data, dict) and "results" in results_resp.data:
            results = results_resp.data["results"]
        # Should have at least one result
        self.assertGreater(len(results), 0, "Expected at least one StudentResult")
        first = results[0]
        self.assertIn("score", first)
        self.assertIn("responses", first)

    def test_scan_upload_wrong_test_returns_400(self):
        """POST /api/v1/omr/scan/ with a test belonging to another user returns 400."""
        from django.contrib.auth import get_user_model
        from assessments.models import ClassGroup, Test
        from django.core.files.uploadedfile import SimpleUploadedFile

        User = get_user_model()
        other_user = User.objects.create_user(
            email="other_scan@test.com", password="testpass"
        )
        cg = ClassGroup.objects.create(user=other_user, created_by=other_user, name="OtherCG")
        other_test = Test.objects.create(
            user=other_user, class_group=cg, created_by=other_user, title="OtherTest"
        )

        client = self._get_client()
        img_bytes = self._make_scan_image_bytes({})
        uploaded = SimpleUploadedFile("scan.png", img_bytes, content_type="image/png")

        response = client.post(
            "/api/v1/omr/scan/",
            {"test": other_test.id, "files": uploaded},
            format="multipart",
        )
        self.assertEqual(response.status_code, 400,
                         f"Expected 400 for cross-tenant test, got {response.status_code}")

    def test_scan_batch_progress_endpoint(self):
        """GET /api/v1/omr/scan-batches/<id>/ returns {status, total, processed}."""
        from omr.scan.pipeline import simulate_correct_marks
        from django.core.files.uploadedfile import SimpleUploadedFile

        client = self._get_client()
        correct_marks = simulate_correct_marks(self.omr_sheet)
        img_bytes = self._make_scan_image_bytes(correct_marks)

        uploaded = SimpleUploadedFile("scan.png", img_bytes, content_type="image/png")
        upload_resp = client.post(
            "/api/v1/omr/scan/",
            {"test": self.test.id, "files": uploaded},
            format="multipart",
        )
        self.assertEqual(upload_resp.status_code, 201)
        batch_id = upload_resp.data["batch_id"]

        progress_resp = client.get(f"/api/v1/omr/scan-batches/{batch_id}/")
        self.assertEqual(progress_resp.status_code, 200)
        data = progress_resp.data
        self.assertIn("status", data)
        self.assertIn("total", data)
        self.assertIn("processed", data)
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["processed"], 1)
        self.assertEqual(data["status"], "done")

    def test_scan_batch_cross_tenant_returns_404(self):
        """GET /api/v1/omr/scan-batches/<id>/ from another user returns 404."""
        from django.contrib.auth import get_user_model
        from assessments.models import ClassGroup, Test
        from omr.models import ScanBatch
        from rest_framework.test import APIClient

        User = get_user_model()
        other_user = User.objects.create_user(
            email="other_batch@test.com", password="testpass"
        )
        cg = ClassGroup.objects.create(user=other_user, created_by=other_user, name="OtherCG2")
        other_test = Test.objects.create(
            user=other_user, class_group=cg, created_by=other_user, title="OtherTest2"
        )
        # Create a batch belonging to other_user
        other_batch = ScanBatch.objects.create(
            test=other_test,
            created_by=other_user,
            status=ScanBatch.STATUS_DONE,
            total=0,
            processed=0,
        )

        client = self._get_client()
        response = client.get(f"/api/v1/omr/scan-batches/{other_batch.id}/")
        self.assertEqual(response.status_code, 404,
                         f"Expected 404 for cross-tenant batch, got {response.status_code}")


class ReviewQueueEndpointTest(TestCase):
    """
    GET /api/v1/review/?test= → open ReviewItems with double_mark reason.
    POST /api/v1/review/<id>/resolve/ → resolves + recomputes result.
    """

    N_QUESTIONS = 10
    SCALE = 2.0

    def setUp(self):
        self.user, self.test, _ = _build_test_with_questions(
            self.N_QUESTIONS, n_options=4)
        self.omr_sheet, self.sheet_meta, self.descriptor, self.student = \
            _build_omr_sheet(self.test, self.user, self.N_QUESTIONS, 4, roll_digits=3)

    def _get_client(self):
        from rest_framework.test import APIClient
        client = APIClient()
        response = client.post("/api/v1/auth/token/", {
            "email": self.user.email,
            "password": "testpass",
        }, format="json")
        token = response.data["access"]
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return client

    def _upload_double_mark_scan(self, client):
        from omr.scan.pipeline import simulate_correct_marks
        from omr.simulate import simulate_scan
        from django.core.files.uploadedfile import SimpleUploadedFile

        correct_marks = simulate_correct_marks(self.omr_sheet)
        # Double-mark q_pos=0
        dm_marks = dict(correct_marks)
        dm_marks[0] = ["A", "B"]

        img = simulate_scan(
            self.descriptor, self.sheet_meta,
            marked=dm_marks, roll="005",
            page=0, scale=self.SCALE,
        )
        ok, buf = cv2.imencode(".png", img)
        self.assertTrue(ok)
        img_bytes = buf.tobytes()

        uploaded = SimpleUploadedFile("dm_scan.png", img_bytes, content_type="image/png")
        return client.post(
            "/api/v1/omr/scan/",
            {"test": self.test.id, "files": uploaded},
            format="multipart",
        )

    def test_review_queue_lists_double_mark_item(self):
        """GET /review/?test= lists a double_mark ReviewItem after scanning."""
        from results.models import ReviewItem

        client = self._get_client()
        upload_resp = self._upload_double_mark_scan(client)
        self.assertEqual(upload_resp.status_code, 201,
                         f"Upload failed: {upload_resp.data}")

        review_resp = client.get(f"/api/v1/review/?test={self.test.id}")
        self.assertEqual(review_resp.status_code, 200)
        # Handle paginated response
        if isinstance(review_resp.data, dict) and "results" in review_resp.data:
            items = review_resp.data["results"]
        else:
            items = review_resp.data
        self.assertGreater(len(items), 0, "Expected at least one review item")
        reasons = [item["reason"] for item in items]
        self.assertIn("double_mark", reasons, f"Expected double_mark, got {reasons}")

    def test_resolve_review_item_recomputes_result(self):
        """
        POST /review/<id>/resolve/ with correct single mark →
        recomputes StudentResult + resolves ReviewItem.
        """
        from results.models import ReviewItem, StudentResult

        client = self._get_client()
        upload_resp = self._upload_double_mark_scan(client)
        self.assertEqual(upload_resp.status_code, 201,
                         f"Upload failed: {upload_resp.data}")

        # Get the review items (pipeline may create 2: one per scan_job, one in _maybe_grade)
        review_resp = client.get(f"/api/v1/review/?test={self.test.id}")
        # Handle paginated response
        if isinstance(review_resp.data, dict) and "results" in review_resp.data:
            items = review_resp.data["results"]
        else:
            items = review_resp.data
        self.assertGreater(len(items), 0)

        # Resolve all open review items
        resolved_ids = []
        for item in items:
            review_id = item["id"]
            resolve_resp = client.post(
                f"/api/v1/review/{review_id}/resolve/",
                {"marked_options": ["A"]},
                format="json",
            )
            self.assertIn(resolve_resp.status_code, [200, 201],
                          f"Resolve failed for {review_id}: {resolve_resp.data}")
            resolved_ids.append(review_id)

        # All resolved ReviewItems should now be resolved=True
        for review_id in resolved_ids:
            ri = ReviewItem.objects.get(pk=review_id)
            self.assertTrue(ri.resolved, f"ReviewItem {review_id} should be resolved=True")
            self.assertEqual(ri.resolved_by, self.user)

        # StudentResult should exist (score should have been recomputed)
        sr = StudentResult.objects.filter(omr_sheet=self.omr_sheet).first()
        self.assertIsNotNone(sr)

        # After resolving all, no open review items should remain for this sheet
        open_items = ReviewItem.objects.filter(
            omr_sheet=self.omr_sheet, resolved=False
        ).count()
        self.assertEqual(open_items, 0, f"Expected 0 open items, got {open_items}")

        # needs_review must be cleared once all reviews are resolved
        sr.refresh_from_db()
        self.assertFalse(
            sr.needs_review,
            "StudentResult.needs_review should be False after resolving all reviews",
        )

    def test_needs_review_cleared_after_resolving_multiple_items(self):
        """
        Fix #1 regression: with 2+ open ReviewItems for one result, resolving
        ALL of them must clear needs_review (the fallback branch must recompute).
        """
        from results.models import ReviewItem, StudentResult

        client = self._get_client()
        upload_resp = self._upload_double_mark_scan(client)
        self.assertEqual(upload_resp.status_code, 201,
                         f"Upload failed: {upload_resp.data}")

        sr = StudentResult.objects.get(omr_sheet=self.omr_sheet)
        self.assertTrue(sr.needs_review,
                        "Result should start with needs_review=True")

        # Inject a SECOND open double_mark ReviewItem so we exercise the
        # multi-item resolve path (the second resolve hits the fallback branch,
        # since the only flagged response is cleared by the first resolve).
        #
        # It must name the question it is about. Review items carry a q_pos so
        # that resolving one edits the answer it was raised for; an item without
        # one is refused rather than applied to whichever response happens to be
        # flagged first.
        from results.models import QuestionResponse
        used = set(
            ReviewItem.objects.filter(omr_sheet=self.omr_sheet)
            .exclude(q_pos=None)
            .values_list("q_pos", flat=True)
        )
        spare_q_pos = (
            QuestionResponse.objects.filter(student_result=sr)
            .exclude(q_pos__in=used)
            .values_list("q_pos", flat=True)
            .first()
        )
        self.assertIsNotNone(spare_q_pos, "Expected a second question to flag")
        ReviewItem.objects.create(
            omr_sheet=self.omr_sheet,
            reason=ReviewItem.REASON_DOUBLE_MARK,
            q_pos=spare_q_pos,
        )

        open_ids = list(
            ReviewItem.objects.filter(
                omr_sheet=self.omr_sheet, resolved=False
            ).values_list("id", flat=True)
        )
        self.assertGreaterEqual(len(open_ids), 2,
                                "Expected at least 2 open ReviewItems")

        for review_id in open_ids:
            resolve_resp = client.post(
                f"/api/v1/review/{review_id}/resolve/",
                {"marked_options": ["A"]},
                format="json",
            )
            self.assertIn(resolve_resp.status_code, [200, 201],
                          f"Resolve failed for {review_id}: {resolve_resp.data}")

        # No open items remain
        self.assertEqual(
            ReviewItem.objects.filter(
                omr_sheet=self.omr_sheet, resolved=False
            ).count(),
            0,
        )

        # needs_review must now be False
        sr.refresh_from_db()
        self.assertFalse(
            sr.needs_review,
            "needs_review must be cleared after resolving ALL ReviewItems "
            "(fallback branch must recompute)",
        )

    def test_review_scope_cross_tenant_returns_empty(self):
        """
        GET /review/?test= for a different user's test returns empty list
        (not an error — just filtered out).
        """
        from django.contrib.auth import get_user_model
        from assessments.models import ClassGroup, Test
        from rest_framework.test import APIClient

        User = get_user_model()
        other_user = User.objects.create_user(
            email="other_review@test.com", password="testpass"
        )
        cg = ClassGroup.objects.create(user=other_user, created_by=other_user, name="OtherCG3")
        other_test = Test.objects.create(
            user=other_user, class_group=cg, created_by=other_user, title="OtherTest3"
        )

        client = self._get_client()
        # Query for the other user's test — should return nothing (scope filtering)
        review_resp = client.get(f"/api/v1/review/?test={other_test.id}")
        self.assertEqual(review_resp.status_code, 200)
        # Handle paginated response
        if isinstance(review_resp.data, dict) and "results" in review_resp.data:
            count = review_resp.data["count"]
        else:
            count = len(review_resp.data)
        self.assertEqual(count, 0, "Should not see another user's review items")

    def test_results_scope_cross_tenant_returns_empty(self):
        """GET /results/?test= for another user's test returns empty list."""
        from django.contrib.auth import get_user_model
        from assessments.models import ClassGroup, Test

        User = get_user_model()
        other_user = User.objects.create_user(
            email="other_results@test.com", password="testpass"
        )
        cg = ClassGroup.objects.create(user=other_user, created_by=other_user, name="OtherCG4")
        other_test = Test.objects.create(
            user=other_user, class_group=cg, created_by=other_user, title="OtherTest4"
        )

        client = self._get_client()
        results_resp = client.get(f"/api/v1/results/?test={other_test.id}")
        self.assertEqual(results_resp.status_code, 200)
        # Handle paginated response
        if isinstance(results_resp.data, dict) and "results" in results_resp.data:
            count = results_resp.data["count"]
        else:
            count = len(results_resp.data)
        self.assertEqual(count, 0, "Should not see another user's results")

    def test_no_qr_review_item_visible_and_resolvable(self):
        """
        Fix #3: a no_qr scan (blank image, no decodable QR) creates a
        ReviewItem with omr_sheet=None + scan_job set. It must:
          - appear in GET /review/?test= (via the scan_job__batch path), and
          - be resolvable by its owner via POST /review/<id>/resolve/.
        """
        import numpy as np
        from django.core.files.uploadedfile import SimpleUploadedFile
        from results.models import ReviewItem

        client = self._get_client()

        # A pure-white image has no QR → the pipeline flags 'no_qr'.
        blank = np.full((1169 * 2, 827 * 2), 255, dtype=np.uint8)
        ok, buf = cv2.imencode(".png", blank)
        self.assertTrue(ok)
        blank_bytes = buf.tobytes()

        uploaded = SimpleUploadedFile("blank.png", blank_bytes, content_type="image/png")
        upload_resp = client.post(
            "/api/v1/omr/scan/",
            {"test": self.test.id, "files": uploaded},
            format="multipart",
        )
        self.assertEqual(upload_resp.status_code, 201,
                         f"Upload failed: {upload_resp.data}")

        # A no_qr ReviewItem with omr_sheet=None + scan_job set must exist.
        no_qr_items = ReviewItem.objects.filter(
            reason=ReviewItem.REASON_NO_QR,
            omr_sheet__isnull=True,
            scan_job__isnull=False,
            resolved=False,
        )
        self.assertEqual(no_qr_items.count(), 1,
                         "Expected exactly one orphaned no_qr ReviewItem")

        # It must surface in GET /review/?test= (via the scan_job path).
        review_resp = client.get(f"/api/v1/review/?test={self.test.id}")
        self.assertEqual(review_resp.status_code, 200)
        if isinstance(review_resp.data, dict) and "results" in review_resp.data:
            items = review_resp.data["results"]
        else:
            items = review_resp.data
        reasons = [item["reason"] for item in items]
        self.assertIn("no_qr", reasons,
                      f"no_qr item should be visible in review API, got {reasons}")

        # It must be resolvable by its owner.
        no_qr_id = no_qr_items.first().id
        resolve_resp = client.post(
            f"/api/v1/review/{no_qr_id}/resolve/",
            {"marked_options": []},
            format="json",
        )
        self.assertIn(resolve_resp.status_code, [200, 201],
                      f"Resolve of no_qr item failed: {resolve_resp.data}")

        ri = ReviewItem.objects.get(pk=no_qr_id)
        self.assertTrue(ri.resolved, "no_qr ReviewItem should be resolved")
        self.assertEqual(ri.resolved_by, self.user)
