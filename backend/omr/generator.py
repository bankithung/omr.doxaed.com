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
    """Draw institution/test/subject/student header text on page 1."""
    # Header area: top of page down to ~HEADER_H px
    from omr.geometry import MARGIN, HEADER_H

    margin_pt = px_len_to_pt(MARGIN)
    header_h_pt = px_len_to_pt(HEADER_H)

    # Column layout: left block (institution+test+subject+student)
    # right area is taken by QR — leave it
    qr_left_pt = px_len_to_pt(sheet.get("_qr_x", 660))  # reserve ~right 20% for QR

    c.setFillColorRGB(0, 0, 0)

    # Institution name (largest text)
    y_top = px_len_to_pt(page_h_px) - margin_pt - 6  # near top
    institution = sheet.get("institution", "")
    test_title = sheet.get("test_title", "")
    subject = sheet.get("subject", "")
    student_name = sheet.get("student_name", "")
    human_code = sheet.get("human_readable_code", "")

    if institution:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(margin_pt, y_top, institution[:60])
        y_top -= 13

    if test_title:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(margin_pt, y_top, test_title[:60])
        y_top -= 13

    if subject:
        c.setFont("Helvetica", 9)
        c.drawString(margin_pt, y_top, f"Subject: {subject[:50]}")
        y_top -= 12

    if student_name:
        c.setFont("Helvetica", 9)
        c.drawString(margin_pt, y_top, f"Name: {student_name[:50]}")
        y_top -= 12

    # Human-readable code (printed below the QR label area)
    c.setFont("Helvetica", 8)
    c.drawString(margin_pt, y_top, f"Sheet ID: {human_code}")


def _draw_roll_grid(c: Canvas, roll_grid: dict, sheet: dict, page_h_px: float) -> None:
    """
    Draw the roll-number dot-grid bubble outlines on page 1.

    Layout: digit-column headers (0, 1, 2 … N-1 → one column per digit place),
    row labels (digit 0–9) on the left, bubble outlines in a grid.
    """
    from omr.geometry import MARGIN

    ox, oy = roll_grid["origin"]           # top of first bubble row (px, top-left)
    col_pitch = roll_grid["col_pitch"]
    row_pitch = roll_grid["row_pitch"]
    radius = roll_grid["radius"]
    cols = roll_grid["cols"]
    rows = roll_grid["rows"]               # always 10

    roll_label = sheet.get("roll_label", "Roll No.")

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

    # Row labels (digit 0–9) + bubble outlines
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
            c.circle(cx_pt, cy_pt, r_pt, fill=0, stroke=1)


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

        c.showPage()

    c.save()
    return buffer.getvalue()
