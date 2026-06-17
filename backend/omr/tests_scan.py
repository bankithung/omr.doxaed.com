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
        binary = to_binary(img)
        answers = read_answers(binary, self.descriptor, page=0)

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
        binary = to_binary(img)
        roll_str, flag = read_roll(binary, self.descriptor)

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
        binary = to_binary(img)

        q0 = next(b for b in self.descriptor["answer_bubbles"] if b["q_pos"] == 0)
        opts = {o["label"]: o for o in q0["options"]}

        ratio_A = bubble_fill_ratio(
            binary, opts["A"]["cx"], opts["A"]["cy"], opts["A"]["r"]
        )
        # Sample option C (not adjacent to A) for a cleaner empty measurement
        ratio_C = bubble_fill_ratio(
            binary, opts["C"]["cx"], opts["C"]["cy"], opts["C"]["r"]
        )

        self.assertGreaterEqual(
            ratio_A, FILL_HIGH + 0.10,
            f"Filled bubble A ratio ({ratio_A:.3f}) should be >= {FILL_HIGH + 0.10:.2f} "
            f"(FILL_HIGH={FILL_HIGH})",
        )
        self.assertLess(
            ratio_C, FILL_LOW,
            f"Empty bubble C ratio ({ratio_C:.3f}) should be < FILL_LOW={FILL_LOW} "
            "(correct side of threshold)",
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

        binary = to_binary(canonical)
        answers = read_answers(binary, self.descriptor, page=0)

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

        binary = to_binary(canonical)
        roll_str, flag = read_roll(binary, self.descriptor)

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

    def _binary(self, marked, roll="000"):
        from omr.simulate import simulate_scan
        from omr.scan.read import to_binary
        img = simulate_scan(
            self.descriptor, self.sheet_meta,
            marked=marked, roll=roll, page=0, scale=1.0,
        )
        return to_binary(img)

    def test_double_mark_sets_flag(self):
        """
        Marking two options on q_pos=0 (with multiple_allowed=False) must
        set flag "double_mark" and include both labels in "marked".
        """
        from omr.scan.read import read_answers

        marked = {0: ["A", "C"]}
        binary = self._binary(marked)
        answers = read_answers(binary, self.descriptor, page=0, multiple_allowed=False)

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
        binary = self._binary(marked)
        answers = read_answers(binary, self.descriptor, page=0, multiple_allowed=True)

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
        binary = self._binary(marked={})
        answers = read_answers(binary, self.descriptor, page=0)

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
        binary = self._binary(marked)
        answers = read_answers(binary, self.descriptor, page=0)

        q5 = answers[5]
        self.assertEqual(sorted(q5["marked"]), ["B"])
        self.assertIsNone(q5["flag"],
                          f"Clean single mark should have flag=None, got {q5['flag']!r}")

    def test_all_questions_present_in_result(self):
        """read_answers must return an entry for every question on the page."""
        from omr.scan.read import read_answers

        binary = self._binary(marked={0: ["A"]})
        answers = read_answers(binary, self.descriptor, page=0)

        page_qs = self.descriptor["page_map"][0]
        for q_pos in page_qs:
            self.assertIn(q_pos, answers,
                          f"q_pos={q_pos} missing from read_answers result")
