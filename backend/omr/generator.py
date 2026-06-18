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

`descriptor` is the dict returned by omr.geometry.build_template().

Coordinate mapping (D1):
    x_pt = x_px / 100.0 * 72
    y_pt = (page_h_px - y_px) / 100.0 * 72
    (ReportLab origin is bottom-left; descriptor uses top-left origin.)
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


def _draw_header(c: Canvas, sheet: dict, page_h_px: float) -> None:
    """Draw institution/test/subject/student header text on page 1.

    Text is indented to clear the TL fiducial quiet zone:
      - x starts at MARGIN + FID + 12 px  (~76 px from left edge)
      - first line's y starts below the fiducial bottom edge (MARGIN + FID + 12 px
        from top, i.e. ~76 px down), so the whole block is to the right of and
        below the TL fiducial square.
    """
    from omr.geometry import MARGIN, FID

    # Horizontal indent: clear the TL fiducial (spans x 40..64) + 12 px quiet zone
    text_left_px = MARGIN + FID + 12   # = 76 px
    text_left_pt = px_len_to_pt(text_left_px)

    c.setFillColorRGB(0, 0, 0)

    # Vertical start: first line baseline sits just below the fiducial bottom edge
    # fiducial bottom = MARGIN + FID = 64 px from top
    # add 12 px quiet zone → 76 px from top
    # convert to ReportLab y (bottom-left origin):
    fid_clear_px = MARGIN + FID + 12   # = 76 px from top
    y_top = px_to_pt(0, fid_clear_px, page_h_px)[1]   # take the y component only

    institution = sheet.get("institution", "")
    test_title = sheet.get("test_title", "")
    subject = sheet.get("subject", "")
    student_name = sheet.get("student_name", "")
    human_code = sheet.get("human_readable_code", "")

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

    # Human-readable code
    c.setFont("Helvetica", 8)
    c.drawString(text_left_pt, y_top, f"Sheet ID: {human_code}")


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
                          page_h_px: float) -> None:
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
        fid_clear_px = MARGIN + FID + 12   # = 76 px from top
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
    descriptor : dict
        Returned by omr.geometry.build_template().

    Returns
    -------
    bytes — the raw PDF content.
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

    for page_no in range(page_count):
        # --- Fiducials (every page) ---
        _draw_fiducials(c, fiducials, page_h_px)

        # --- QR code (every page) ---
        _draw_qr(c, qr_desc, sheet_code, page_no, page_count, page_h_px)

        # --- Header text (page 1 only) ---
        if page_no == 0:
            _draw_header(c, sheet, page_h_px)
            _draw_roll_grid(c, roll_grid, sheet, page_h_px)

        # --- Answer bubbles for this page ---
        _draw_answer_bubbles(c, answer_bubbles, page_no, page_h_px)

        # --- Section headers (gated; no-op for legacy sheets) ---
        _draw_section_headers(c, descriptor, page_no, page_h_px)

        c.showPage()

    c.save()
    return buffer.getvalue()
