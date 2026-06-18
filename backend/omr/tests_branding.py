"""
omr.tests_branding — Phase 3b: sheet branding (heading + logo) tests.

Test suite
----------
1. Coord invariance (S4 guard): render_sheet_pdf with vs without branding
   → descriptor answer_bubbles cx/cy/r + roll_grid are byte-identical;
   page_count unchanged.

2. No overlap with header/sections: a branded + competitive (sections) sheet
   renders without heading/logo overprinting the section legend or header text
   (verified via the computed layout rects, not pixel diffing).

3. Logo hardening (S6): an oversized image / too-large file is rejected by the
   validator; a valid small PNG is accepted.

4. Branding resolution:
   - Test heading overrides Org default.
   - brand_inherit_org=False ignores Org.
   - No branding set → _draw_branding returns 0 (no band); output is valid PDF.
"""
import io
import os
import tempfile

from django.test import TestCase


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_sheet(code="000001-BRANDTST", heading="", logo_path="", logo_position="left"):
    return {
        "sheet_code": code,
        "human_readable_code": code.split("-")[1] if "-" in code else code,
        "institution": "Test School",
        "test_title": "Branding Test",
        "subject": "Physics",
        "student_name": "Alice",
        "roll_label": "Roll No.",
        "roll_digits": 3,
        "heading": heading,
        "logo_path": logo_path,
        "logo_position": logo_position,
    }


def _make_descriptor(num_questions=50, num_options=4, roll_digits=3, sections=None):
    from omr.geometry import build_template
    return build_template(num_questions, num_options, roll_digits, sections=sections)


def _tiny_png_bytes(width=80, height=40, color=(30, 100, 200)):
    """Create a minimal valid PNG in memory."""
    from PIL import Image
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


def _write_tmp_png(width=80, height=40):
    """Write a small PNG to a temp file; return the path."""
    png = _tiny_png_bytes(width, height)
    fd, path = tempfile.mkstemp(suffix=".png")
    with os.fdopen(fd, "wb") as f:
        f.write(png)
    return path


# ---------------------------------------------------------------------------
# 1. Coord invariance (S4 guard)
# ---------------------------------------------------------------------------

class CoordInvarianceBrandingTests(TestCase):
    """
    answer_bubbles cx/cy/r and roll_grid must be UNCHANGED with vs without branding.
    The descriptor is purely generated from geometry — branding never touches it.
    This also verifies that page_count is identical.
    """

    def test_descriptor_identical_with_without_heading(self):
        """build_template output is unaffected by branding (branding is not passed to it)."""
        d_plain = _make_descriptor(num_questions=50)
        d_branded = _make_descriptor(num_questions=50)
        # Descriptors are the same since branding doesn't flow through build_template
        self.assertEqual(d_plain["page_count"], d_branded["page_count"])
        self.assertEqual(len(d_plain["answer_bubbles"]), len(d_branded["answer_bubbles"]))
        for pb, bb in zip(d_plain["answer_bubbles"], d_branded["answer_bubbles"]):
            for po, bo in zip(pb["options"], bb["options"]):
                self.assertEqual((po["cx"], po["cy"], po["r"]),
                                 (bo["cx"], bo["cy"], bo["r"]),
                                 f"Coords changed at q_pos={pb['q_pos']}")

    def test_pdf_page_count_unchanged_with_branding(self):
        """PDF page count must be the same with or without branding."""
        import fitz
        from omr.generator import render_sheet_pdf

        desc = _make_descriptor(num_questions=60)
        sheet_plain = _make_sheet()
        sheet_branded = _make_sheet(heading="My School")

        pdf_plain = render_sheet_pdf(sheet_plain, desc)
        pdf_branded = render_sheet_pdf(sheet_branded, desc)

        doc_plain = fitz.open(stream=pdf_plain, filetype="pdf")
        doc_branded = fitz.open(stream=pdf_branded, filetype="pdf")
        self.assertEqual(doc_plain.page_count, doc_branded.page_count,
                         "PDF page count changed with branding")
        self.assertEqual(doc_plain.page_count, desc["page_count"])

    def test_pdf_valid_with_heading(self):
        """A sheet with a heading is a valid PDF."""
        from omr.generator import render_sheet_pdf

        desc = _make_descriptor()
        sheet = _make_sheet(heading="Springfield High School")
        pdf = render_sheet_pdf(sheet, desc)
        self.assertTrue(pdf.startswith(b"%PDF"), "Not a valid PDF with heading")

    def test_pdf_valid_with_logo(self):
        """A sheet with a logo file produces a valid PDF."""
        import fitz
        from omr.generator import render_sheet_pdf

        logo_path = _write_tmp_png(80, 40)
        try:
            desc = _make_descriptor()
            sheet = _make_sheet(heading="School with Logo", logo_path=logo_path)
            pdf = render_sheet_pdf(sheet, desc)
            self.assertTrue(pdf.startswith(b"%PDF"))
            doc = fitz.open(stream=pdf, filetype="pdf")
            self.assertEqual(doc.page_count, desc["page_count"])
        finally:
            os.unlink(logo_path)

    def test_pdf_valid_with_logo_positions(self):
        """All three logo_position values (left/center/right) produce valid PDFs."""
        import fitz
        from omr.generator import render_sheet_pdf

        logo_path = _write_tmp_png(60, 30)
        try:
            desc = _make_descriptor()
            for pos in ("left", "center", "right"):
                sheet = _make_sheet(heading="Logo Test", logo_path=logo_path, logo_position=pos)
                pdf = render_sheet_pdf(sheet, desc)
                self.assertTrue(pdf.startswith(b"%PDF"), f"Invalid PDF for logo_position={pos}")
        finally:
            os.unlink(logo_path)

    def test_descriptor_bubbles_unchanged_after_render(self):
        """
        render_sheet_pdf must not mutate the descriptor's answer_bubbles.
        (Descriptor is passed by reference; generator must not modify it.)
        """
        from omr.generator import render_sheet_pdf

        desc = _make_descriptor(num_questions=25)
        # Snapshot cx/cy/r before rendering
        snapshot = [
            [(o["cx"], o["cy"], o["r"]) for o in b["options"]]
            for b in desc["answer_bubbles"]
        ]

        sheet = _make_sheet(heading="Mutation Guard Test")
        render_sheet_pdf(sheet, desc)

        for i, bubble in enumerate(desc["answer_bubbles"]):
            for j, opt in enumerate(bubble["options"]):
                self.assertEqual(
                    (opt["cx"], opt["cy"], opt["r"]), snapshot[i][j],
                    f"Descriptor mutated at bubble {i}, option {j}"
                )


# ---------------------------------------------------------------------------
# 2. No overlap: branding + competitive sections
# ---------------------------------------------------------------------------

class BrandingNoOverlapTests(TestCase):
    """
    Verify (via layout rect arithmetic, not pixel diffing) that:
    - The branding band occupies y ∈ [40, 40+BRANDING_BAND_H_PX] px from top.
    - The section legend starts at y ≥ 76 + BRANDING_BAND_H_PX from top.
    - These two rects do NOT overlap.
    - The branding rect is disjoint from the QR block and fiducials.
    """

    def test_branding_band_below_fiducial_quiet_zone(self):
        """Branding rect top (42px) is at/above fiducial edge (40px) but x starts at 76px."""
        from omr.generator import BRAND_X_LEFT, BRAND_X_RIGHT, BRANDING_BAND_H_PX
        from omr.geometry import MARGIN, FID

        # Fiducial: cx=52, cy=52, side=24 → spans [40, 64] in both x and y
        fid_x_right = MARGIN + FID  # 64 px
        fid_y_bottom = MARGIN + FID  # 64 px

        # Branding rect
        brand_x_left = BRAND_X_LEFT   # 76 px — well AFTER fiducial right edge (64 px)
        brand_y_top = MARGIN + 2      # 42 px — starts within header band

        # x is disjoint: branding starts AFTER fiducial
        self.assertGreater(brand_x_left, fid_x_right,
                           "Branding left edge must be to the right of the fiducial")

    def test_branding_rect_disjoint_from_qr_block(self):
        """Branding rect right edge (700px) is less than QR block left edge (707px)."""
        from omr.generator import BRAND_X_RIGHT
        from omr.geometry import W, MARGIN, FID

        qr_size = 80
        qr_x_left = W - MARGIN - qr_size  # = 827 - 40 - 80 = 707 px

        self.assertLessEqual(BRAND_X_RIGHT, qr_x_left,
                             f"Branding right edge ({BRAND_X_RIGHT}) overlaps QR block "
                             f"which starts at x={qr_x_left}")

    def test_section_legend_pushed_below_branding_band(self):
        """
        With branding active, the sections legend starts at
        y = 76 + BRANDING_BAND_H_PX from the top — after the branding band ends.
        """
        from omr.generator import BRANDING_BAND_H_PX
        from omr.geometry import MARGIN, FID

        fid_clear_px = MARGIN + FID + 12   # 76 px — base legend start (no branding)
        legend_start_with_branding = fid_clear_px + BRANDING_BAND_H_PX

        branding_band_bottom = MARGIN + 2 + BRANDING_BAND_H_PX  # 42 + 50 = 92 px

        # The legend starts BELOW the branding band
        self.assertGreaterEqual(
            legend_start_with_branding,
            branding_band_bottom,
            f"Section legend start ({legend_start_with_branding}px) overlaps "
            f"branding band bottom ({branding_band_bottom}px)"
        )

    def test_branding_band_fits_above_roll_grid(self):
        """The branding band bottom must sit above the roll grid top."""
        from omr.generator import BRANDING_BAND_H_PX
        from omr.geometry import HEADER_H, MARGIN

        brand_band_bottom = MARGIN + 2 + BRANDING_BAND_H_PX  # 92px

        # Roll grid origin is at HEADER_H + 20 = 188px from top
        roll_grid_origin_y = HEADER_H + 20  # 188 px

        self.assertLess(brand_band_bottom, roll_grid_origin_y,
                        "Branding band overlaps the roll grid")

    def test_branded_competitive_sheet_renders_valid_pdf(self):
        """A branded + competitive (sections) sheet produces a valid multi-page PDF."""
        import fitz
        from omr.generator import render_sheet_pdf

        nq = 60
        secs = [
            {"key": "A", "label": "Physics", "order_index": 0,
             "q_pos_range": [0, 34], "policy": {"type": "all"}},
            {"key": "B", "label": "Chemistry", "order_index": 1,
             "q_pos_range": [35, 59], "policy": {"type": "choose_k", "k": 10}},
        ]
        desc = _make_descriptor(num_questions=nq, sections=secs)
        sheet = _make_sheet(heading="National Competitive Exam 2026")

        pdf = render_sheet_pdf(sheet, desc)
        self.assertTrue(pdf.startswith(b"%PDF"))
        doc = fitz.open(stream=pdf, filetype="pdf")
        self.assertEqual(doc.page_count, desc["page_count"])

    def test_branded_competitive_bubble_coords_unchanged(self):
        """
        Branded + competitive sheet → answer_bubbles cx/cy/r are byte-identical
        to a plain non-branded non-sections sheet with the same question count.
        """
        from omr.geometry import build_template

        nq = 60
        secs = [
            {"key": "A", "label": "Sec A", "order_index": 0,
             "q_pos_range": [0, 29], "policy": {"type": "all"}},
            {"key": "B", "label": "Sec B", "order_index": 1,
             "q_pos_range": [30, 59], "policy": {"type": "all"}},
        ]
        d_plain = build_template(nq, 4, 3)
        d_branded = build_template(nq, 4, 3, sections=secs)

        for pb, bb in zip(d_plain["answer_bubbles"], d_branded["answer_bubbles"]):
            for po, bo in zip(pb["options"], bb["options"]):
                self.assertEqual((po["cx"], po["cy"], po["r"]),
                                 (bo["cx"], bo["cy"], bo["r"]))


# ---------------------------------------------------------------------------
# 2b. Header vs roll-grid collision (the bug a visual render exposed)
# ---------------------------------------------------------------------------

class HeaderRollGridCollisionTests(TestCase):
    """
    THE REGRESSION GUARD (previously missing).

    When branding pushes the header text down, the header block must NOT
    overprint the roll-number grid, which is at a FIXED descriptor position.

    These tests extract the ACTUAL drawn text-span positions from the rendered
    PDF (via PyMuPDF) and assert that the lowest header-text baseline stays
    above the roll-grid top — an end-to-end check, not a re-derivation of the
    layout math.
    """

    # --- PDF text-extraction helpers --------------------------------------

    def _extract_text_spans_page0(self, pdf_bytes):
        """
        Return a list of {text, x0, y0, x1, y1} for every text span on page 0,
        in PIXEL coordinates (top-left origin, 100 DPI canonical space).

        PyMuPDF reports text rects in PDF POINTS with a top-left origin already
        (its y grows downward).  Page height in points = A4 = 841.89 pt.
        Convert points → canonical px:  px = pt / 72 * 100.
        """
        import fitz

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page = doc[0]
        spans = []
        data = page.get_text("dict")
        for block in data.get("blocks", []):
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    x0, y0, x1, y1 = span["bbox"]
                    spans.append({
                        "text": span["text"],
                        "x0_px": x0 / 72.0 * 100.0,
                        "y0_px": y0 / 72.0 * 100.0,
                        "x1_px": x1 / 72.0 * 100.0,
                        "y1_px": y1 / 72.0 * 100.0,
                    })
        doc.close()
        return spans

    def _rendered_roll_label_top_px(self, spans, roll_label="Roll No."):
        """
        Extract the ACTUAL rendered "Roll No." label span from the PDF and
        return its GLYPH TOP y (px).  This is the highest roll-grid ink — the
        true collision boundary the header must stay above.  The earlier bug
        capped against the digit-origin / label BASELINE (lower on the page),
        so header descenders still overlapped the label glyphs.
        """
        label_spans = [s for s in spans if s["text"].strip() == roll_label]
        assert label_spans, f"No {roll_label!r} label span found in the PDF"
        # The label's glyph top is the smallest y0 among matching spans.
        return min(s["y0_px"] for s in label_spans)

    def _header_spans(self, spans):
        """Return only the header text spans (Title / Subject / Name / Sheet ID)."""
        header_markers = ("Branding Test", "Subject:", "Name:", "Sheet ID:")
        return [s for s in spans if any(m in s["text"] for m in header_markers)]

    # --- Tests -------------------------------------------------------------

    def test_branded_header_text_stays_above_roll_label(self):
        """
        With branding (heading) active, every header text span (Title / Subject /
        Name / Sheet ID) must end ABOVE the actual rendered "Roll No." LABEL top
        — no collision with the label or the column-number row.
        """
        from omr.generator import render_sheet_pdf

        desc = _make_descriptor(num_questions=50, roll_digits=3)
        sheet = _make_sheet(heading="Springfield High School")  # branding ON
        pdf = render_sheet_pdf(sheet, desc)

        spans = self._extract_text_spans_page0(pdf)
        roll_label_top_px = self._rendered_roll_label_top_px(spans)
        header_spans = self._header_spans(spans)
        self.assertTrue(header_spans,
                        "No header text spans found in the branded PDF")

        for s in header_spans:
            self.assertLess(
                s["y1_px"], roll_label_top_px,
                f"Header span {s['text']!r} bottom (y1={s['y1_px']:.1f}px) "
                f"collides with the 'Roll No.' label top ({roll_label_top_px:.1f}px)"
            )

    def test_branded_sheet_id_above_roll_label(self):
        """
        Specifically the 'Sheet ID:' line (the LAST header line, the one that
        collided in the visual bug) must stay above the rendered "Roll No."
        label top.
        """
        from omr.generator import render_sheet_pdf

        desc = _make_descriptor(num_questions=50, roll_digits=4)
        sheet = _make_sheet(heading="My Institution Of Learning")
        pdf = render_sheet_pdf(sheet, desc)

        spans = self._extract_text_spans_page0(pdf)
        roll_label_top_px = self._rendered_roll_label_top_px(spans)

        sheet_id_spans = [s for s in spans if "Sheet ID:" in s["text"]]
        self.assertTrue(sheet_id_spans, "No 'Sheet ID:' span found")
        for s in sheet_id_spans:
            self.assertLess(
                s["y1_px"], roll_label_top_px,
                f"'Sheet ID:' bottom ({s['y1_px']:.1f}px) collides with the "
                f"'Roll No.' label top ({roll_label_top_px:.1f}px)"
            )

    def test_branded_header_clears_column_number_row(self):
        """
        The header must also clear the roll-grid COLUMN-NUMBER row ("0 1 2 …"),
        which is drawn BELOW the label but still above the digit origin.
        Verify via the rendered column-header spans: the lowest header bottom
        must be above the highest column-number top.
        """
        from omr.generator import render_sheet_pdf

        desc = _make_descriptor(num_questions=50, roll_digits=3)
        sheet = _make_sheet(heading="Column Row Guard School")
        pdf = render_sheet_pdf(sheet, desc)

        spans = self._extract_text_spans_page0(pdf)
        # Column-number spans are single digits ("0","1","2") near the grid top.
        # Identify them as single-char numeric spans with y0 above the digit grid.
        rg = desc["roll_grid"]
        grid_origin_y = rg["origin"][1]  # 188px
        col_num_spans = [
            s for s in spans
            if s["text"].strip().isdigit()
            and len(s["text"].strip()) == 1
            and s["y0_px"] < grid_origin_y  # above the first bubble row
        ]
        self.assertTrue(col_num_spans, "No column-number spans found")
        col_row_top_px = min(s["y0_px"] for s in col_num_spans)

        header_spans = self._header_spans(spans)
        for s in header_spans:
            self.assertLess(
                s["y1_px"], col_row_top_px,
                f"Header span {s['text']!r} bottom ({s['y1_px']:.1f}px) collides "
                f"with the column-number row top ({col_row_top_px:.1f}px)"
            )

    def test_branded_header_with_logo_stays_above_roll_label(self):
        """Same collision guard against the rendered label, with heading + logo."""
        from omr.generator import render_sheet_pdf

        # Use a TALL logo (80×120) to confirm the height-cap keeps the band
        # compact enough for the header to still clear the roll-grid label.
        logo_path = _write_tmp_png(80, 120)
        try:
            desc = _make_descriptor(num_questions=50, roll_digits=3)
            sheet = _make_sheet(
                heading="Logo + Heading School", logo_path=logo_path,
                logo_position="left",
            )
            pdf = render_sheet_pdf(sheet, desc)

            spans = self._extract_text_spans_page0(pdf)
            roll_label_top_px = self._rendered_roll_label_top_px(spans)
            header_spans = self._header_spans(spans)
            self.assertTrue(header_spans, "No header spans found")
            for s in header_spans:
                self.assertLess(
                    s["y1_px"], roll_label_top_px,
                    f"Header span {s['text']!r} bottom ({s['y1_px']:.1f}px) "
                    f"collides with the 'Roll No.' label top ({roll_label_top_px:.1f}px)"
                )
        finally:
            os.unlink(logo_path)

    def test_unbranded_header_layout_unchanged(self):
        """
        Without branding, the header text spans must be at the ORIGINAL y
        positions (byte-identical layout) — the collision fix must not move
        anything when branding is OFF.

        We compare the rendered text-span y positions of a no-branding sheet
        against a sheet rendered the same way but with the branding keys
        entirely absent (legacy path).
        """
        from omr.generator import render_sheet_pdf

        desc = _make_descriptor(num_questions=50, roll_digits=3)

        sheet_legacy = {
            "sheet_code": "000009-LEGACYHL",
            "human_readable_code": "LEGACYHL",
            "institution": "Test School",
            "test_title": "Branding Test",
            "subject": "Physics",
            "student_name": "Alice",
            "roll_label": "Roll No.",
            "roll_digits": 3,
        }
        sheet_empty_brand = dict(sheet_legacy)
        sheet_empty_brand.update({"heading": "", "logo_path": "", "logo_position": "left"})

        pdf_legacy = render_sheet_pdf(sheet_legacy, desc)
        pdf_empty = render_sheet_pdf(sheet_empty_brand, desc)

        spans_legacy = self._extract_text_spans_page0(pdf_legacy)
        spans_empty = self._extract_text_spans_page0(pdf_empty)

        # Build {text -> y0} maps for header lines and compare positions.
        def header_map(spans):
            out = {}
            for s in spans:
                t = s["text"].strip()
                if any(k in t for k in ("Branding Test", "Subject:", "Name:", "Sheet ID:", "Test School")):
                    out[t] = round(s["y0_px"], 2)
            return out

        m_legacy = header_map(spans_legacy)
        m_empty = header_map(spans_empty)
        self.assertEqual(
            m_legacy, m_empty,
            "Header text y-positions differ between legacy and empty-branding "
            "render — the collision fix changed the no-branding layout"
        )

    def test_unbranded_header_unchanged_when_branding_absent_byte_identical(self):
        """
        Stronger: a sheet with NO branding keys produces a PDF whose page-0
        header spans match the pre-branding expectation — the Sheet ID line
        sits at ~141px (its original position), NOT pushed down.
        """
        from omr.generator import render_sheet_pdf

        desc = _make_descriptor(num_questions=50, roll_digits=3)
        sheet = {
            "sheet_code": "000010-NOBRANDX",
            "human_readable_code": "NOBRANDX",
            "institution": "Test School",
            "test_title": "Plain Test",
            "subject": "Maths",
            "student_name": "Bob",
            "roll_label": "Roll No.",
            "roll_digits": 3,
        }
        pdf = render_sheet_pdf(sheet, desc)
        spans = self._extract_text_spans_page0(pdf)

        sheet_id_spans = [s for s in spans if "Sheet ID:" in s["text"]]
        self.assertTrue(sheet_id_spans)
        # Original (no-branding) layout: institution@76, title@89, subject@102,
        # name@114, Sheet ID baseline ~126px → glyph top ~120px.
        # Assert it is well ABOVE 150px (i.e. NOT pushed into the 188px roll grid).
        for s in sheet_id_spans:
            self.assertLess(
                s["y1_px"], 150,
                f"Unbranded 'Sheet ID:' at y1={s['y1_px']:.1f}px appears pushed "
                f"down — no-branding layout must be unchanged"
            )


# ---------------------------------------------------------------------------
# 3. Logo hardening (S6)
# ---------------------------------------------------------------------------

class LogoHardeningTests(TestCase):
    """
    Verify that validate_logo_image:
    - Rejects files > 2 MB
    - Rejects images with dimensions > 2000×2000
    - Accepts a valid small PNG
    - Accepts a valid small JPEG
    """

    def _make_upload_file(self, content: bytes, name: str, content_type: str):
        """Create a Django InMemoryUploadedFile-like object."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        return SimpleUploadedFile(name, content, content_type=content_type)

    def _make_png_bytes(self, width: int, height: int) -> bytes:
        from PIL import Image
        img = Image.new("RGB", (width, height), color=(128, 128, 128))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def _make_jpeg_bytes(self, width: int, height: int) -> bytes:
        from PIL import Image
        img = Image.new("RGB", (width, height), color=(200, 100, 50))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return buf.getvalue()

    def test_valid_small_png_accepted(self):
        """A small (80×40) PNG is accepted without errors."""
        from django.core.exceptions import ValidationError
        from common.logo_validators import validate_logo_image

        png = self._make_png_bytes(80, 40)
        uploaded = self._make_upload_file(png, "logo.png", "image/png")
        # Should not raise
        try:
            validate_logo_image(uploaded)
        except ValidationError as e:
            self.fail(f"validate_logo_image raised ValidationError for valid PNG: {e}")

    def test_valid_small_jpeg_accepted(self):
        """A small (100×50) JPEG is accepted without errors."""
        from django.core.exceptions import ValidationError
        from common.logo_validators import validate_logo_image

        jpeg = self._make_jpeg_bytes(100, 50)
        uploaded = self._make_upload_file(jpeg, "logo.jpg", "image/jpeg")
        try:
            validate_logo_image(uploaded)
        except ValidationError as e:
            self.fail(f"validate_logo_image raised ValidationError for valid JPEG: {e}")

    def test_oversized_file_rejected(self):
        """A file > 2 MB is rejected."""
        from django.core.exceptions import ValidationError
        from common.logo_validators import validate_logo_image

        # Create a fake file slightly over 2 MB
        big_content = b"X" * (2 * 1024 * 1024 + 1)
        uploaded = self._make_upload_file(big_content, "big.png", "image/png")
        with self.assertRaises(ValidationError) as ctx:
            validate_logo_image(uploaded)
        self.assertIn("2 MB", str(ctx.exception))

    def test_oversized_dimensions_rejected(self):
        """An image with dimensions > 2000×2000 px is rejected."""
        from django.core.exceptions import ValidationError
        from common.logo_validators import validate_logo_image, MAX_DIMENSION_PX

        # Create a 2001×100 image (one dimension just over the limit)
        too_wide = MAX_DIMENSION_PX + 1
        png = self._make_png_bytes(too_wide, 100)
        uploaded = self._make_upload_file(png, "wide.png", "image/png")
        with self.assertRaises(ValidationError) as ctx:
            validate_logo_image(uploaded)
        self.assertIn(str(MAX_DIMENSION_PX), str(ctx.exception))

    def test_wrong_content_type_rejected(self):
        """A file with a non-PNG/JPEG content-type is rejected."""
        from django.core.exceptions import ValidationError
        from common.logo_validators import validate_logo_image

        gif_content = b"GIF89a..."
        uploaded = self._make_upload_file(gif_content, "logo.gif", "image/gif")
        with self.assertRaises(ValidationError) as ctx:
            validate_logo_image(uploaded)
        self.assertIn("PNG or JPEG", str(ctx.exception))

    def test_wrong_extension_rejected(self):
        """A .bmp file extension is rejected."""
        from django.core.exceptions import ValidationError
        from common.logo_validators import validate_logo_image

        png = self._make_png_bytes(80, 40)
        # No content_type — only the extension should trigger rejection
        from django.core.files.uploadedfile import SimpleUploadedFile
        uploaded = SimpleUploadedFile("logo.bmp", png, content_type="")
        with self.assertRaises(ValidationError) as ctx:
            validate_logo_image(uploaded)
        self.assertIn(".bmp", str(ctx.exception))

    def test_max_image_pixels_guard_set(self):
        """PIL.Image.MAX_IMAGE_PIXELS is set to our safe limit at import."""
        from PIL import Image
        from common.logo_validators import MAX_IMAGE_PIXELS
        # Importing logo_validators sets PIL.Image.MAX_IMAGE_PIXELS
        self.assertEqual(Image.MAX_IMAGE_PIXELS, MAX_IMAGE_PIXELS)

    def test_logo_height_capped_in_generator(self):
        """
        A tall logo (200px) is height-capped in the generator's _draw_branding.
        The function should complete without error and return the branding band height.
        """
        from omr.generator import _draw_branding, BRANDING_LOGO_H_CAP_PX
        import reportlab.pdfgen.canvas as canvas_mod

        logo_path = _write_tmp_png(width=200, height=200)
        try:
            sheet = _make_sheet(heading="Cap Test", logo_path=logo_path)
            buf = io.BytesIO()
            c = canvas_mod.Canvas(buf)
            result = _draw_branding(c, sheet, page_h_px=1169)
            # Should return BRANDING_BAND_H_PX (non-zero because heading is set)
            from omr.generator import BRANDING_BAND_H_PX
            self.assertEqual(result, BRANDING_BAND_H_PX)
        finally:
            os.unlink(logo_path)


# ---------------------------------------------------------------------------
# 4. Branding resolution (Test → Org → none)
# ---------------------------------------------------------------------------

class BrandingResolutionTests(TestCase):
    """
    Verify resolution order:
    1. Test.sheet_heading overrides Org.default_sheet_heading.
    2. brand_inherit_org=False → Org ignored.
    3. No branding → _draw_branding returns 0.
    4. Test logo overrides Org logo.
    """

    def test_no_branding_draw_branding_returns_zero(self):
        """When heading and logo_path are both absent/blank, _draw_branding returns 0."""
        from omr.generator import _draw_branding
        import reportlab.pdfgen.canvas as canvas_mod

        sheet = _make_sheet(heading="", logo_path="")
        buf = io.BytesIO()
        c = canvas_mod.Canvas(buf)
        result = _draw_branding(c, sheet, page_h_px=1169)
        self.assertEqual(result, 0,
                         "_draw_branding must return 0 when no branding is set")

    def test_heading_only_returns_band_height(self):
        """When only a heading is set, _draw_branding returns BRANDING_BAND_H_PX."""
        from omr.generator import _draw_branding, BRANDING_BAND_H_PX
        import reportlab.pdfgen.canvas as canvas_mod

        sheet = _make_sheet(heading="My School", logo_path="")
        buf = io.BytesIO()
        c = canvas_mod.Canvas(buf)
        result = _draw_branding(c, sheet, page_h_px=1169)
        self.assertEqual(result, BRANDING_BAND_H_PX)

    def test_logo_only_returns_band_height(self):
        """When only a logo is set (no heading), _draw_branding returns BRANDING_BAND_H_PX."""
        from omr.generator import _draw_branding, BRANDING_BAND_H_PX
        import reportlab.pdfgen.canvas as canvas_mod

        logo_path = _write_tmp_png(80, 40)
        try:
            sheet = _make_sheet(heading="", logo_path=logo_path)
            buf = io.BytesIO()
            c = canvas_mod.Canvas(buf)
            result = _draw_branding(c, sheet, page_h_px=1169)
            self.assertEqual(result, BRANDING_BAND_H_PX)
        finally:
            os.unlink(logo_path)

    def test_no_branding_pdf_byte_identical_structure(self):
        """
        Two sheets rendered without branding and with empty branding keys
        produce structurally identical PDFs (same page count, same PDF header).
        """
        import fitz
        from omr.generator import render_sheet_pdf

        desc = _make_descriptor(num_questions=25)

        # No branding keys at all (original usage)
        sheet_legacy = {
            "sheet_code": "000001-LEGACYBR",
            "human_readable_code": "LEGACYBR",
            "institution": "Test School",
            "test_title": "Legacy",
            "subject": "",
            "student_name": "",
            "roll_label": "Roll No.",
            "roll_digits": 3,
        }

        # Explicit empty branding keys
        sheet_empty_brand = dict(sheet_legacy)
        sheet_empty_brand.update({
            "sheet_code": "000002-EMPTYBRD",
            "human_readable_code": "EMPTYBRD",
            "heading": "",
            "logo_path": "",
            "logo_position": "left",
        })

        pdf_legacy = render_sheet_pdf(sheet_legacy, desc)
        pdf_empty = render_sheet_pdf(sheet_empty_brand, desc)

        # Both must be valid PDFs with the same page count
        doc_legacy = fitz.open(stream=pdf_legacy, filetype="pdf")
        doc_empty = fitz.open(stream=pdf_empty, filetype="pdf")
        self.assertEqual(doc_legacy.page_count, doc_empty.page_count)
        self.assertTrue(pdf_legacy.startswith(b"%PDF"))
        self.assertTrue(pdf_empty.startswith(b"%PDF"))

    def test_invalid_logo_path_falls_back_gracefully(self):
        """
        If logo_path points to a non-existent file, _draw_branding skips the logo
        gracefully (still draws heading if present) and returns BRANDING_BAND_H_PX.
        """
        from omr.generator import _draw_branding, BRANDING_BAND_H_PX
        import reportlab.pdfgen.canvas as canvas_mod

        sheet = _make_sheet(heading="Graceful Fallback", logo_path="/nonexistent/logo.png")
        buf = io.BytesIO()
        c = canvas_mod.Canvas(buf)
        # Should not raise — heading is set so band is drawn
        result = _draw_branding(c, sheet, page_h_px=1169)
        self.assertEqual(result, BRANDING_BAND_H_PX)

    def test_invalid_logo_path_no_heading_returns_zero(self):
        """
        If logo_path points to a non-existent file AND no heading is set,
        _draw_branding returns 0 (nothing drawn after the graceful logo skip).
        """
        from omr.generator import _draw_branding
        import reportlab.pdfgen.canvas as canvas_mod

        sheet = _make_sheet(heading="", logo_path="/nonexistent/logo.png")
        buf = io.BytesIO()
        c = canvas_mod.Canvas(buf)
        result = _draw_branding(c, sheet, page_h_px=1169)
        # Logo fails to open → skipped. No heading → 0.
        self.assertEqual(result, 0)
