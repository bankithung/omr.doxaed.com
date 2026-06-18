"""
omr.generator — ReportLab PDF renderer for OMR answer sheets.

Entry point:
    render_sheet_pdf(sheet, descriptor) -> bytes

`sheet` dict keys required:
    sheet_code           str   e.g. "000042-AB3DEFGH"
    human_readable_code  str   e.g. "AB3DEFGH"
    institution          str   Header: institution name
    test_title           str   Header: test/exam title
    subject              str   Header: subject (may be empty)
    student_name         str   Header: student name (may be empty)
    roll_label           str   Header label for roll grid (e.g. "Roll No.")
    roll_digits          int   Number of digit columns in roll grid

Optional branding keys (Phase 3b — page 1 only; absence → output byte-identical):
    heading              str   Branding heading text (e.g. institution name for header)
    logo_path            str   Absolute filesystem path to logo image (PNG/JPEG)
    logo_position        str   "left" | "center" | "right"

`descriptor` is the dict returned by omr.geometry.build_template().

Coordinate mapping (D1):
    x_pt = x_px / 100.0 * 72
    y_pt = (page_h_px - y_px) / 100.0 * 72
    (ReportLab origin is bottom-left; descriptor uses top-left origin.)

Branding layout (S4 — header re-layout):
    Safe branding rect: x ∈ [76, 700], y ∈ [40, 86] px (top-left origin).
    This is disjoint from:
      - TL fiducial (cx=52, cy=52 → covers [40,64]×[40,64]) — branding starts
        x=76 which is AFTER the fiducial quiet zone.
      - QR block (x ∈ [707, 787]) — branding stops at x=700.
      - Roll grid (origin_y = 188) — header band ends at 168px.
      - Answer bubbles (start at ~340px on page 1).
    When branding is active, heading+logo occupy y ∈ [40, BRANDING_BAND_H] px.
    The header text (_draw_header) and section legend (_draw_section_headers)
    are pushed DOWN by BRANDING_BAND_H so nothing overprints.
    When branding is absent, BRANDING_BAND_H = 0 and output is byte-identical.
"""
import io

import qrcode
from PIL import Image as PILImage
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas


# ---------------------------------------------------------------------------
# Coordinate conversion helpers
# ---------------------------------------------------------------------------

def px_to_pt(x_px: float, y_px: float, page_h_px: float) -> tuple[float, float]:
    """Convert descriptor pixel coords (top-left origin) to ReportLab points (bottom-left)."""
    x_pt = x_px / 100.0 * 72.0
    y_pt = (page_h_px - y_px) / 100.0 * 72.0
    return x_pt, y_pt


def px_len_to_pt(length_px: float) -> float:
    """Convert a pixel length/size to points."""
    return length_px / 100.0 * 72.0


# ---------------------------------------------------------------------------
# QR code generation
# ---------------------------------------------------------------------------

def _make_qr_image(data: str) -> PILImage.Image:
    """Render a QR code string to a Pillow Image (RGB)."""
    qr = qrcode.QRCode(
        version=None,          # auto-size
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    return img


# ---------------------------------------------------------------------------
# Branding layout constants (Phase 3b)
# ---------------------------------------------------------------------------

# Vertical budget for the WHOLE top band on page 1, measured from the header
# text top (MARGIN + FID + 12 = 76 px) down to the HIGHEST roll-grid ink (the
# "Roll No." label glyph top ≈ 158 px) → ~82 px total.  This budget MUST hold:
#   [branding band] + [4 header text lines] + safety gaps
# so the branding band is kept deliberately COMPACT (small logo) — a smaller
# logo is acceptable per the spec — leaving the header room to clear the roll
# grid label.
#
# Vertical height reserved for the branding band when branding IS present.
# This is how many pixels the existing header text is pushed down.
# Heading line height ~14px (Helvetica-Bold 11pt ≈ 13px at 100DPI; use 14).
# Logo height cap = 28px so the band stays ≤ 34px, leaving ~44px for the
# 4-line header above the roll-grid label.
BRANDING_HEADING_H_PX = 16   # px reserved for heading text line
BRANDING_LOGO_H_CAP_PX = 28  # logo is height-capped at this many px (compact)
BRANDING_GAP_PX = 6          # gap between branding band bottom and first header line
# Total branding band height (pushed down = this value when branding present)
BRANDING_BAND_H_PX = max(BRANDING_HEADING_H_PX, BRANDING_LOGO_H_CAP_PX) + BRANDING_GAP_PX
# 34px: heading 16 + gap 6 = 22; logo 28 + gap 6 = 34 → 34px

# Horizontal safe zone for branding (px, top-left origin)
BRAND_X_LEFT = 76    # clear of TL fiducial quiet zone
BRAND_X_RIGHT = 700  # clear of QR block (starts at 707)


# ---------------------------------------------------------------------------
# Branding draw pass (Phase 3b)
# ---------------------------------------------------------------------------

def _draw_branding(c: Canvas, sheet: dict, page_h_px: float) -> int:
    """
    Draw the optional heading and/or logo in the top of the header band.

    Returns the branding band height in pixels (BRANDING_BAND_H_PX) when
    branding was drawn, or 0 when there is nothing to draw (so callers can
    push their text down by this amount).

    Parameters
    ----------
    c          : ReportLab Canvas
    sheet      : sheet dict — may contain 'heading', 'logo_path', 'logo_position'
    page_h_px  : page height in pixels

    Safe rect
    ---------
    x : [BRAND_X_LEFT, BRAND_X_RIGHT]  (76..700 px)
    y : [40, 40 + BRANDING_BAND_H_PX]  (40..90 px from top)
    Disjoint from TL fiducial, QR block, roll grid, answer bubbles.

    S4 invariant: this function NEVER changes any cx/cy/r coordinates.
    The descriptor is not touched. Absence of branding → returns 0 (caller
    draws at the normal y position → byte-identical output).

    S6 defense: PIL.Image.MAX_IMAGE_PIXELS is set in common.logo_validators
    at import time. Additionally, we guard here before opening the file.
    """
    from common.logo_validators import MAX_IMAGE_PIXELS, MAX_DIMENSION_PX

    heading = sheet.get("heading", "") or ""
    logo_path = sheet.get("logo_path", "") or ""
    logo_position = sheet.get("logo_position", "left") or "left"

    if not heading and not logo_path:
        return 0  # nothing to draw → output unchanged

    # Vertical anchor: branding band top = MARGIN px from top (same as fiducial top)
    # We use y = 42px from top (just inside the safe zone, below the page edge margin)
    from omr.geometry import MARGIN
    band_top_px = MARGIN + 2  # 42 px from top

    # Branding rect in ReportLab coords
    # Note: y in RL is (page_h - y_px) / 100 * 72, increasing upward.
    brand_left_pt = px_len_to_pt(BRAND_X_LEFT)

    c.setFillColorRGB(0, 0, 0)

    # ---- Draw logo ----
    logo_drawn = False   # True if the logo was successfully drawn
    logo_drawn_h_px = 0
    logo_drawn_w_pt = 0.0

    if logo_path:
        try:
            # S6: guard MAX_IMAGE_PIXELS before opening
            PILImage.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS

            pil_img = PILImage.open(logo_path)
            orig_w, orig_h = pil_img.size

            # Validate dimensions defensively at draw time (belt+suspenders over model validator)
            if orig_w <= MAX_DIMENSION_PX and orig_h <= MAX_DIMENSION_PX:
                # Height-cap: logo height ≤ BRANDING_LOGO_H_CAP_PX
                cap_h_px = BRANDING_LOGO_H_CAP_PX
                if orig_h <= cap_h_px:
                    draw_h_px = orig_h
                    draw_w_px = orig_w
                else:
                    scale = cap_h_px / orig_h
                    draw_h_px = cap_h_px
                    draw_w_px = int(orig_w * scale)

                draw_h_pt = px_len_to_pt(draw_h_px)
                draw_w_pt = px_len_to_pt(draw_w_px)

                # Clamp width to safe rect
                max_logo_w_pt = px_len_to_pt(BRAND_X_RIGHT - BRAND_X_LEFT)
                if draw_w_pt > max_logo_w_pt:
                    draw_w_pt = max_logo_w_pt
                    draw_h_pt = draw_h_pt * (max_logo_w_pt / px_len_to_pt(draw_w_px))

                # Determine x position based on logo_position
                if logo_position == "right":
                    logo_x_px = BRAND_X_RIGHT - int(draw_w_pt / 72.0 * 100)
                    logo_x_px = max(logo_x_px, BRAND_X_LEFT)
                elif logo_position == "center":
                    center_px = (BRAND_X_LEFT + BRAND_X_RIGHT) // 2
                    logo_x_px = center_px - int(draw_w_pt / 72.0 * 100) // 2
                    logo_x_px = max(logo_x_px, BRAND_X_LEFT)
                else:  # left
                    logo_x_px = BRAND_X_LEFT

                logo_x_pt = px_len_to_pt(logo_x_px)

                # Vertical: top of logo at band_top_px
                # In ReportLab (bottom-left origin), the bottom-left of the image:
                logo_top_px = band_top_px
                logo_bottom_px = logo_top_px + draw_h_px
                _, logo_bottom_y_pt = px_to_pt(0, logo_bottom_px, page_h_px)

                pil_img_rgb = pil_img.convert("RGB")
                img_reader = ImageReader(pil_img_rgb)
                c.drawImage(
                    img_reader,
                    logo_x_pt, logo_bottom_y_pt,
                    width=draw_w_pt, height=draw_h_pt,
                    preserveAspectRatio=True, mask="auto",
                )
                logo_drawn = True
                logo_drawn_h_px = draw_h_px
                logo_drawn_w_pt = draw_w_pt
        except Exception:
            # On any draw-time error, skip the logo gracefully
            pass

    # ---- Draw heading text ----
    if heading:
        # Place heading text in the safe rect.
        # If logo was drawn on the left: heading to the right of the logo.
        # If logo is right: heading on the left.
        # Otherwise: heading at the left edge.
        if logo_drawn and logo_position == "left":
            heading_x_pt = brand_left_pt + logo_drawn_w_pt + px_len_to_pt(6)
        else:
            heading_x_pt = brand_left_pt

        # Vertical: centre the heading in the branding band
        heading_mid_px = band_top_px + BRANDING_BAND_H_PX // 2
        _, heading_y_pt = px_to_pt(0, heading_mid_px, page_h_px)

        c.setFont("Helvetica-Bold", 12)
        # Truncate heading to fit safe rect width
        max_heading_chars = 65
        heading_text = heading[:max_heading_chars]
        c.drawString(heading_x_pt, heading_y_pt, heading_text)

    # Return band height if anything was actually drawn; 0 otherwise
    if heading or logo_drawn:
        return BRANDING_BAND_H_PX
    return 0


# ---------------------------------------------------------------------------
# Per-page drawing helpers
# ---------------------------------------------------------------------------

def _draw_fiducials(c: Canvas, fiducials: list, page_h_px: float) -> None:
    """Draw 4 solid black fiducial squares from descriptor fiducial list."""
    from omr.geometry import FID
    half = px_len_to_pt(FID / 2.0)
    c.setFillColorRGB(0, 0, 0)
    c.setStrokeColorRGB(0, 0, 0)
    for fid in fiducials:
        cx_pt, cy_pt = px_to_pt(fid["cx"], fid["cy"], page_h_px)
        c.rect(cx_pt - half, cy_pt - half, half * 2, half * 2, fill=1, stroke=0)


def _draw_qr(c: Canvas, qr_desc: dict, sheet_code: str, page: int, total: int,
             page_h_px: float) -> None:
    """Generate and draw the QR code for this page."""
    payload = f"{sheet_code}|{page + 1}|{total}"
    qr_img = _make_qr_image(payload)

    x_pt, y_pt = px_to_pt(qr_desc["x"], qr_desc["y"], page_h_px)
    size_pt = px_len_to_pt(qr_desc["size"])
    # y_pt is the top of the QR in ReportLab coords (after flip)
    # reportlab drawImage: x,y is the bottom-left corner
    y_bottom_pt = y_pt - size_pt

    c.drawImage(ImageReader(qr_img), x_pt, y_bottom_pt, width=size_pt, height=size_pt)


# Ascent (px) of the roll-grid "Roll No." label glyphs above their baseline.
# The label is Helvetica-Bold 8pt; at 100 DPI its cap/ascender ink reaches
# ~12 px above the baseline (measured from the rendered PDF: baseline 166 px →
# glyph top 154.4 px → ascent ≈ 11.6 px).  We round UP to 12 so the cap is
# conservative — the header must clear the actual glyph top, not the baseline.
ROLL_LABEL_ASCENT_PX = 12


def _roll_grid_label_top_px(roll_grid: dict | None = None) -> float:
    """
    Return the y (px from top) of the HIGHEST ink in the roll-grid label band.

    The roll grid is at a FIXED descriptor position.  Its topmost drawn element
    is the "Roll No." LABEL, whose BASELINE is at origin_y - row_pitch - 2.
    Because drawString's y is the baseline, the label's GLYPH TOP sits
    ROLL_LABEL_ASCENT_PX above that baseline.  The header text block must stay
    above this glyph top (minus a safety margin) — NOT merely above the
    digit-origin or the label baseline (the earlier bug capped against the
    baseline and the header descenders still collided with the label glyphs).

    When roll_grid is None, falls back to constant geometry:
        (HEADER_H + 20) - 20 - 2 - ROLL_LABEL_ASCENT_PX = 154 px
    """
    if roll_grid is not None:
        oy = roll_grid["origin"][1]
        row_pitch = roll_grid["row_pitch"]
        label_baseline = oy - row_pitch - 2
    else:
        from omr.geometry import HEADER_H
        label_baseline = (HEADER_H + 20) - 20 - 2  # 166 px
    return label_baseline - ROLL_LABEL_ASCENT_PX  # glyph top (≈ 154 px)


def _draw_header(c: Canvas, sheet: dict, page_h_px: float,
                 branding_push_px: int = 0, roll_grid: dict | None = None) -> None:
    """Draw institution/test/subject/student header text on page 1.

    Text is indented to clear the TL fiducial quiet zone:
      - x starts at MARGIN + FID + 12 px  (~76 px from left edge)
      - first line's y starts below the fiducial bottom edge (MARGIN + FID + 12 px
        from top, i.e. ~76 px down), so the whole block is to the right of and
        below the TL fiducial square.

    Parameters
    ----------
    branding_push_px : int
        When branding is active, this is the number of extra pixels to push
        the header text DOWN (i.e. increase the top-y offset) so it starts
        below the branding band.  0 → byte-identical to the pre-branding layout.
    roll_grid : dict | None
        The descriptor's roll_grid block.  Used (only when branding is active)
        to CAP the header text block so its lowest baseline stays above the
        fixed roll-grid label — no overprint.  When branding is OFF
        (branding_push_px == 0) the layout is byte-identical to before and the
        roll_grid arg is ignored (the original block always fit).

    Collision-avoidance (when branding_push_px > 0)
    -----------------------------------------------
    The branding band consumes space at the top of the header, but the roll
    grid is at a FIXED y.  Pushing the full header block down by the band
    height would drive the last lines INTO the roll grid.  So when branding is
    active we:
      1. Drop the redundant "institution" line (the branding heading already
         carries the institution name).
      2. Shrink the per-line leading / font so the remaining lines (title,
         subject, name, Sheet ID) fit in the space between the branding band
         bottom and the roll-grid label top — never overlapping it.
    """
    from omr.geometry import MARGIN, FID

    # Horizontal indent: clear the TL fiducial (spans x 40..64) + 12 px quiet zone
    text_left_px = MARGIN + FID + 12   # = 76 px
    text_left_pt = px_len_to_pt(text_left_px)

    c.setFillColorRGB(0, 0, 0)

    institution = sheet.get("institution", "")
    test_title = sheet.get("test_title", "")
    subject = sheet.get("subject", "")
    student_name = sheet.get("student_name", "")
    human_code = sheet.get("human_readable_code", "")

    # ----- No branding: original layout (byte-identical to pre-branding) -----
    if branding_push_px <= 0:
        fid_clear_px = MARGIN + FID + 12   # = 76 px from top
        y_top = px_to_pt(0, fid_clear_px, page_h_px)[1]

        if institution:
            c.setFont("Helvetica-Bold", 11)
            c.drawString(text_left_pt, y_top, institution[:60])
            y_top -= 13

        if test_title:
            c.setFont("Helvetica-Bold", 10)
            c.drawString(text_left_pt, y_top, test_title[:60])
            y_top -= 13

        if subject:
            c.setFont("Helvetica", 9)
            c.drawString(text_left_pt, y_top, f"Subject: {subject[:50]}")
            y_top -= 12

        if student_name:
            c.setFont("Helvetica", 9)
            c.drawString(text_left_pt, y_top, f"Name: {student_name[:50]}")
            y_top -= 12

        c.setFont("Helvetica", 8)
        c.drawString(text_left_pt, y_top, f"Sheet ID: {human_code}")
        return

    # ----- Branding active: fit the header BETWEEN the band and the roll grid -
    # Top of the header text block (px from top): below the branding band.
    block_top_px = MARGIN + FID + 12 + branding_push_px   # 76 + push

    # Bottom limit (px from top): the HIGHEST roll-grid ink (the "Roll No."
    # label GLYPH TOP), minus a safety gap.  The LOWEST header glyph BOTTOM
    # (baseline + descender/font-box) must stay above this — so even the last
    # line's descenders clear the roll-grid label.
    label_top_px = _roll_grid_label_top_px(roll_grid)
    SAFETY_GAP_PX = 4
    bottom_limit_px = label_top_px - SAFETY_GAP_PX   # lowest allowed glyph bottom

    # Build the line list (DROP the redundant institution line — the branding
    # heading already shows it).  Each entry: (font_name, font_size, text).
    lines: list[tuple[str, int, str]] = []
    if test_title:
        lines.append(("Helvetica-Bold", 10, test_title[:60]))
    if subject:
        lines.append(("Helvetica", 9, f"Subject: {subject[:50]}"))
    if student_name:
        lines.append(("Helvetica", 9, f"Name: {student_name[:50]}"))
    lines.append(("Helvetica", 8, f"Sheet ID: {human_code}"))

    n = len(lines)
    if n <= 0:
        return

    # Glyph extent below the baseline.  PyMuPDF reports a span's bottom (y1) as
    # roughly baseline + 0.30×font for Helvetica (descender + font-box slack);
    # use 0.30 so our clearance check matches the rendered geometry.
    DESCENDER_FRAC = 0.30

    # Pick a per-line leading (px).  We must place n baselines so that:
    #   - the FIRST line's glyph top  >= block_top_px
    #   - the LAST line's glyph bottom <= bottom_limit_px
    # The first baseline is ~leading below block_top (ascent ≈ leading), and the
    # last baseline is (n-1)*leading below the first.  The last glyph bottom is
    # last_baseline + DESCENDER_FRAC*font.  Solve a comfortable leading, then
    # clamp the whole block so the last line clears the limit regardless.
    DEFAULT_LEADING = 11
    MIN_LEADING = 7
    available_px = max(0, bottom_limit_px - block_top_px)
    leading_px = available_px // n
    leading_px = max(MIN_LEADING, min(DEFAULT_LEADING, leading_px))

    # First baseline: one leading below the block top (so the first glyph top
    # sits at ~block_top_px).
    first_baseline_px = block_top_px + leading_px

    # Last line's font (for descender) — the Sheet ID line is the smallest font.
    last_font = lines[-1][1]
    last_baseline_px = first_baseline_px + (n - 1) * leading_px
    last_glyph_bottom_px = last_baseline_px + DESCENDER_FRAC * last_font

    # If the last line would cross the limit, shift the WHOLE block UP so the
    # last glyph bottom lands exactly on the limit (the block still starts below
    # the branding band because available_px was computed from block_top_px).
    if last_glyph_bottom_px > bottom_limit_px:
        shift = last_glyph_bottom_px - bottom_limit_px
        first_baseline_px -= shift

    y_baseline_px = first_baseline_px
    for font_name, font_size, text in lines:
        eff_size = min(font_size, max(6, leading_px - 1))
        c.setFont(font_name, eff_size)
        _, y_pt = px_to_pt(0, y_baseline_px, page_h_px)
        c.drawString(text_left_pt, y_pt, text)
        y_baseline_px += leading_px


def _draw_roll_grid(c: Canvas, roll_grid: dict, sheet: dict, page_h_px: float) -> None:
    """
    Draw the roll-number dot-grid bubble outlines on page 1.

    Layout: digit-column headers (0, 1, 2 … N-1 → one column per digit place),
    row labels (digit 0–9) on the left, bubble outlines in a grid.

    When roll_grid["prefilled"] is True AND sheet["roll_value"] is set, draws
    solid filled discs at the appropriate digit row for each column so that the
    roll is pre-marked for the student.  The disc is drawn at the full bubble
    radius (r_pt) so the inner-disc sampler (r*0.6) lands on solid black ink and
    reads well above FILL_HIGH (0.45) after Otsu binarisation.
    """
    from omr.geometry import MARGIN

    ox, oy = roll_grid["origin"]           # top of first bubble row (px, top-left)
    col_pitch = roll_grid["col_pitch"]
    row_pitch = roll_grid["row_pitch"]
    radius = roll_grid["radius"]
    cols = roll_grid["cols"]
    rows = roll_grid["rows"]               # always 10

    roll_label = sheet.get("roll_label", "Roll No.")

    # Determine which cells to pre-fill (Mode B)
    prefilled = roll_grid.get("prefilled", False)
    roll_value = sheet.get("roll_value", "") if prefilled else ""
    prefilled_cells: dict[int, int] = {}  # col_idx → digit (row)
    if prefilled and roll_value:
        for col_idx, digit_char in enumerate(roll_value):
            if col_idx >= cols:
                break
            if digit_char.isdigit():
                prefilled_cells[col_idx] = int(digit_char)

    # Label above the grid
    c.setFont("Helvetica-Bold", 8)
    label_x_pt, label_y_pt = px_to_pt(ox - 4, oy - row_pitch - 2, page_h_px)
    c.drawString(label_x_pt, label_y_pt, roll_label)

    # Digit-column headers (0 … cols-1)
    c.setFont("Helvetica", 7)
    for col in range(cols):
        cx = ox + col * col_pitch
        hx_pt, hy_pt = px_to_pt(cx, oy - row_pitch // 2 - 4, page_h_px)
        c.drawCentredString(hx_pt, hy_pt, str(col))

    # Row labels (digit 0–9) + bubble outlines (+ solid fill for pre-bubbled)
    r_pt = px_len_to_pt(radius)
    c.setStrokeColorRGB(0, 0, 0)
    c.setFillColorRGB(0, 0, 0)

    for row in range(rows):
        cy = oy + row * row_pitch
        # Row label: the digit 0-9
        lx_pt, ly_pt = px_to_pt(ox - col_pitch // 2, cy, page_h_px)
        c.setFont("Helvetica", 7)
        c.drawCentredString(lx_pt, ly_pt, str(row))

        for col in range(cols):
            cx = ox + col * col_pitch
            cx_pt, cy_pt = px_to_pt(cx, cy, page_h_px)

            # Check if this cell should be pre-filled (solid disc)
            if col in prefilled_cells and prefilled_cells[col] == row:
                # Solid filled disc at full radius — the inner sampler (r*0.6)
                # will land on solid black ink → fill ratio ≈ 1.0, well above
                # FILL_HIGH (0.45).  Draw outline ring on top for visual clarity.
                c.circle(cx_pt, cy_pt, r_pt, fill=1, stroke=1)
            else:
                # Normal empty bubble outline only
                c.circle(cx_pt, cy_pt, r_pt, fill=0, stroke=1)


def _draw_section_headers(c: Canvas, descriptor: dict, page_no: int,
                          page_h_px: float,
                          branding_push_px: int = 0) -> None:
    """
    Draw a compact section legend in the existing top-header whitespace.

    This function is gated on descriptor.get("sections") — when the key is
    absent (standard/legacy sheets) it is a no-op and the output is
    byte-identical to the pre-sections generator.

    Implementation note (C2 invariant):
        Section labels are drawn ONLY in existing whitespace — the legend
        text lives in the header area on page 1 (right column) and as a
        small inline marker in the question-number gutter on subsequent
        pages.  _draw_answer_bubbles is never touched; no cx/cy coordinates
        change.

    Legend format on page 1 (below Sheet ID line, in the right column):
        "Sections: A — Physics (Q1–35, all)  ·  B — CSAT (attempt any 10 of 15)"
    On pages > 0: omit the legend (no header area); section start markers are
    drawn as small bold labels in the gutter ("§A", "§B") next to the first
    question number of that section on that page.

    Parameters
    ----------
    branding_push_px : int
        When branding is active, the sections legend is pushed DOWN by this
        many pixels so it doesn't overprint the branding band.  0 → identical
        to the pre-branding layout (no-op for non-branded sheets).
    """
    sections = descriptor.get("sections")
    if not sections:
        return

    from omr.geometry import MARGIN, FID

    # ----- Page 1: draw a compact legend in header whitespace -----
    if page_no == 0:
        # Use the right-column area in the header (below "Sheet ID:" line,
        # right of the roll grid).  Right half starts at W//2 from left.
        from omr.geometry import W
        right_col_left_px = W // 2
        right_col_left_pt = px_len_to_pt(right_col_left_px)

        # Vertical start: just below the fiducial bottom edge + quiet zone
        # (same anchor as _draw_header uses for its first line).
        # Plus any branding push to avoid overprinting the branding band.
        fid_clear_px = MARGIN + FID + 12 + branding_push_px   # = 76 px + push
        y_top = px_to_pt(0, fid_clear_px, page_h_px)[1]

        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(right_col_left_pt, y_top, "Sections:")
        y_top -= 10

        c.setFont("Helvetica", 6)
        for sec in sorted(sections, key=lambda s: s.get("order_index", 0)):
            lo, hi = sec["q_pos_range"][0], sec["q_pos_range"][1]
            policy_info = sec.get("policy", {})
            if isinstance(policy_info, dict):
                ptype = policy_info.get("type", "all")
                k = policy_info.get("k")
            else:
                ptype = str(policy_info)
                k = None

            if ptype == "choose_k" and k:
                policy_str = f"attempt any {k} of {hi - lo + 1}"
            else:
                policy_str = "all"

            # Print as 1-based question numbers for human readability
            label_text = (
                f"{sec['key']} — {sec['label']}  "
                f"(Q{lo + 1}–{hi + 1}, {policy_str})"
            )
            # Truncate to fit the right half width
            max_chars = 55
            if len(label_text) > max_chars:
                label_text = label_text[: max_chars - 1] + "…"
            c.drawString(right_col_left_pt, y_top, label_text)
            y_top -= 9

    # ----- All pages: draw small gutter markers at section start rows -----
    # Filter sections whose first q_pos falls on this page.
    # Build lookup: first q_pos of each section on this page.
    answer_bubbles = descriptor.get("answer_bubbles", [])
    q_pos_to_bubble = {b["q_pos"]: b for b in answer_bubbles if b["page"] == page_no}

    for sec in sections:
        lo = sec["q_pos_range"][0]
        if lo not in q_pos_to_bubble:
            continue   # section doesn't start on this page
        bubble = q_pos_to_bubble[lo]
        if not bubble["options"]:
            continue

        first_opt = bubble["options"][0]
        # Draw a small bold marker in the gutter, just to the left of the Q-label
        from omr.geometry import OPTION_PITCH
        label_offset_pt = px_len_to_pt(OPTION_PITCH)
        gutter_x_pt, cy_pt = px_to_pt(first_opt["cx"], first_opt["cy"], page_h_px)
        gutter_x_pt -= label_offset_pt * 1.5  # further left of the Q-number

        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica-Bold", 5)
        marker = f"§{sec['key']}"  # e.g. "§A"
        c.drawCentredString(gutter_x_pt, cy_pt - 2, marker)


def _draw_answer_bubbles(c: Canvas, answer_bubbles: list, page_no: int,
                         page_h_px: float) -> None:
    """
    Draw answer bubbles for a specific page.

    For each question on this page: print the question number (1-indexed),
    then for each option: the option letter + circle outline.
    """
    # Filter to questions on this page
    page_bubbles = [b for b in answer_bubbles if b["page"] == page_no]

    c.setStrokeColorRGB(0, 0, 0)
    c.setFillColorRGB(0, 0, 0)

    for bubble in page_bubbles:
        q_pos = bubble["q_pos"]           # 0-indexed
        options = bubble["options"]

        if not options:
            continue

        # Use first option's cy as the row's y — all options share the same cy
        first_opt = options[0]
        first_cx_pt, first_cy_pt = px_to_pt(first_opt["cx"], first_opt["cy"], page_h_px)
        r_pt = px_len_to_pt(first_opt["r"])

        # Question number label: printed 1-indexed, placed left of the first bubble
        q_label = str(q_pos + 1)
        # Position the number label to the left of the option row
        from omr.geometry import OPTION_PITCH
        label_offset_pt = px_len_to_pt(OPTION_PITCH)
        label_x = first_cx_pt - label_offset_pt
        c.setFont("Helvetica", 6)
        c.drawCentredString(label_x, first_cy_pt - 2, q_label)

        # Option bubbles
        for opt in options:
            cx_pt, cy_pt = px_to_pt(opt["cx"], opt["cy"], page_h_px)
            r_pt = px_len_to_pt(opt["r"])

            # Circle outline
            c.circle(cx_pt, cy_pt, r_pt, fill=0, stroke=1)

            # Option label letter (above or centred in the circle)
            c.setFont("Helvetica", 6)
            c.drawCentredString(cx_pt, cy_pt - 2, opt["label"])


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def render_sheet_pdf(sheet: dict, descriptor: dict) -> bytes:
    """
    Render a single OMR sheet to PDF bytes.

    Parameters
    ----------
    sheet : dict
        Must contain: sheet_code, human_readable_code, institution, test_title,
        subject, student_name, roll_label, roll_digits.
        Optional branding keys: heading, logo_path, logo_position.
    descriptor : dict
        Returned by omr.geometry.build_template().

    Returns
    -------
    bytes — the raw PDF content.

    S4 invariant: when 'heading' and 'logo_path' are absent (or blank),
    the output is byte-identical to the pre-branding implementation.
    The descriptor is never mutated and answer_bubbles cx/cy/r never change.
    """
    sheet_code = sheet["sheet_code"]
    page_count = descriptor["page_count"]
    page_h_px = descriptor["page_px"][1]

    fiducials = descriptor["fiducials"]
    qr_desc = descriptor["qr"]
    roll_grid = descriptor["roll_grid"]
    answer_bubbles = descriptor["answer_bubbles"]

    # Expose QR x position to header drawer for space reservation
    sheet = dict(sheet)  # local copy
    sheet["_qr_x"] = qr_desc["x"]

    buffer = io.BytesIO()
    c = Canvas(buffer, pagesize=A4)

    # Suppress variable metadata to aid determinism (no timestamp in producer tag)
    c.setProducer("omrflow-generator")
    c.setTitle(sheet_code)

    # Resolve branding push once (only page 1 uses it)
    branding_push_px = 0

    for page_no in range(page_count):
        # --- Fiducials (every page) ---
        _draw_fiducials(c, fiducials, page_h_px)

        # --- QR code (every page) ---
        _draw_qr(c, qr_desc, sheet_code, page_no, page_count, page_h_px)

        # --- Branding + Header text (page 1 only) ---
        if page_no == 0:
            # _draw_branding returns how many px the header text must be pushed down.
            branding_push_px = _draw_branding(c, sheet, page_h_px)
            # Pass roll_grid so the header is capped ABOVE the fixed roll grid
            # when branding pushes it down (no collision).
            _draw_header(c, sheet, page_h_px,
                         branding_push_px=branding_push_px, roll_grid=roll_grid)
            _draw_roll_grid(c, roll_grid, sheet, page_h_px)

        # --- Answer bubbles for this page ---
        _draw_answer_bubbles(c, answer_bubbles, page_no, page_h_px)

        # --- Section headers (gated; no-op for legacy sheets) ---
        # Branding push only applies to page 1's legend; gutter markers on
        # other pages are not affected.
        page_brand_push = branding_push_px if page_no == 0 else 0
        _draw_section_headers(c, descriptor, page_no, page_h_px,
                              branding_push_px=page_brand_push)

        c.showPage()

    c.save()
    return buffer.getvalue()
