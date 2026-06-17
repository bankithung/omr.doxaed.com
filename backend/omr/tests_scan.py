"""
Tests for omr.simulate — synthetic scan simulator (Task 2, Phase 4).

TDD: these tests define the contract that simulate.py must satisfy.
"""

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
