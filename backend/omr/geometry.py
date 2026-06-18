"""
omr.geometry — canonical pixel-space template descriptor.

All coordinates use a top-left origin, 100 DPI, A4 portrait (827 × 1169 px).
The generator maps these pixel coordinates to ReportLab points via:
    x_pt = x_px / 100 * 72
    y_pt = (H_px - y_px) / 100 * 72
"""
import math

# ---------------------------------------------------------------------------
# Constants — D1
# ---------------------------------------------------------------------------
DPI = 100
W = 827        # A4 width  at 100 DPI
H = 1169       # A4 height at 100 DPI

MARGIN = 40    # minimum safe margin from edge (px)

FID = 24       # fiducial square side length (px)
FID_R = FID // 2   # half-side; centre offset from edge

# Header band (page 1) — space reserved at the very top for QR + title.
# Set to 168 px so that the roll grid (origin_y = HEADER_H + 20 = 188 px) starts
# well below the header text block. The header begins at y ≈ MARGIN + FID + 12 =
# 76 px and spans ~5 lines × 13 px ≈ 65 px → ends ~141 px. The "Roll No." label is
# drawn at origin_y - row_pitch - 2 ≈ 166 px, leaving ~25 px of clear separation
# between the last header line and the roll-grid label/column headers.
HEADER_H = 168  # px

# Bubble radius for answer grid
R = 9          # px

# Roll-grid bubble radius
ROLL_R = 8     # px

# Answer grid layout
ANSWER_ROWS_PER_COL = 25
ANSWERS_PER_PAGE = 2 * ANSWER_ROWS_PER_COL   # 50

# Option horizontal spacing inside a question row
OPTION_PITCH = 22   # px between option bubble centres


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_template(num_questions: int, num_options: int, roll_digits: int,
                   roll_kind: str = "writein",
                   sections: list | None = None) -> dict:
    """
    Return a descriptor dict containing canonical pixel-space positions for all
    elements on the OMR sheet.

    Parameters
    ----------
    num_questions : int   Total questions in the test (≥ 1).
    num_options   : int   Options per question, clamped to [2, 6].
    roll_digits   : int   Number of digit columns in the roll-number grid (≥ 1).
    roll_kind     : str   "writein" (default) | "prebubbled" | "none".
                          "prebubbled" sets roll_grid.prefilled = True so the generator
                          knows to draw solid fill discs for the assigned roll value.
    sections      : list | None
                          Optional list of section dicts for competitive tests.
                          Each dict: {key, label, order_index, q_pos_range:[lo, hi],
                          policy:{type, k}}.
                          When None/absent → legacy descriptor (no "sections" key).
                          IMPORTANT (C2): adding sections does NOT change any
                          answer_bubbles cx/cy/r — section labels are rendered only
                          in existing header/legend whitespace by the generator.

    Returns
    -------
    dict with keys:
        page_px        [W, H]
        dpi            int
        fiducials      list[{cx, cy}]
        roll_grid      {origin, col_pitch, row_pitch, radius, cols, rows,
                        kind, prefilled}
        qr             {x, y, size}
        answer_bubbles list[{q_pos, page, options:[{label, cx, cy, r}]}]
        page_count     int
        page_map       {page_index: [q_pos, ...]}
        sections       list[{key, label, order_index, q_pos_range, policy,
                        page}]  — only present when sections param is provided
    """
    num_options = max(2, min(6, num_options))
    page_count = math.ceil(num_questions / ANSWERS_PER_PAGE)

    fiducials = _fiducials()
    qr = _qr()
    roll_grid = _roll_grid(roll_digits, roll_kind=roll_kind)
    answer_bubbles, page_map = _answer_grid(num_questions, num_options, page_count)

    descriptor = {
        "page_px": [W, H],
        "dpi": DPI,
        "fiducials": fiducials,
        "roll_grid": roll_grid,
        "qr": qr,
        "answer_bubbles": answer_bubbles,
        "page_count": page_count,
        "page_map": page_map,
    }

    # --- Optional sections block (additive — never changes cx/cy/r) ----------
    # Per C2: answer bubble coordinates are rigid and must be byte-identical
    # with or without a sections block. Sections are pure metadata used only
    # by the generator's _draw_section_headers pass.
    if sections:
        # Build a q_pos → page lookup from the already-computed answer_bubbles
        q_pos_to_page = {b["q_pos"]: b["page"] for b in answer_bubbles}

        sections_out = []
        for sec in sections:
            q_pos_range = sec.get("q_pos_range", [0, num_questions - 1])
            lo, hi = q_pos_range[0], q_pos_range[1]
            # Determine page(s) for this section's first q_pos (for header placement)
            page_no = q_pos_to_page.get(lo, 0)
            sections_out.append({
                "key": sec["key"],
                "label": sec.get("label", sec["key"]),
                "order_index": sec.get("order_index", 0),
                "q_pos_range": q_pos_range,
                "policy": sec.get("policy", {"type": "all"}),
                "page": page_no,
            })

        descriptor["sections"] = sections_out

        # Tag each answer_bubble with its section key (additive dict key; no cx/cy change)
        for bubble in answer_bubbles:
            qp = bubble["q_pos"]
            bubble_section = None
            for sec in sections_out:
                lo, hi = sec["q_pos_range"][0], sec["q_pos_range"][1]
                if lo <= qp <= hi:
                    bubble_section = sec["key"]
                    break
            if bubble_section is not None:
                bubble["section"] = bubble_section

    return descriptor


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _fiducials():
    """
    4 solid black squares (side FID px) centred ~(MARGIN + FID/2) inside each
    corner.  Centres listed TL → TR → BL → BR.
    """
    offset = MARGIN + FID_R   # centre is this many px from each edge
    return [
        {"cx": offset,     "cy": offset},       # top-left
        {"cx": W - offset, "cy": offset},       # top-right
        {"cx": offset,     "cy": H - offset},   # bottom-left
        {"cx": W - offset, "cy": H - offset},   # bottom-right
    ]


def _qr():
    """
    QR block placed in the top-right of the header band, clear of the TR
    fiducial.  We use size=80 px (≈ module size 8 for a version-2 code).
    """
    size = 80
    # x: right-align inside safe margin, clear of TR fiducial (MARGIN + FID)
    x = W - MARGIN - size
    # y: just below the fiducial square's bottom edge, staying inside HEADER_H
    fid_bottom = MARGIN + FID   # bottom edge of top-right fiducial square
    y = fid_bottom + 4          # 4 px gap
    # Ensure it fits vertically
    assert y + size <= H, "QR extends below page"
    return {"x": x, "y": y, "size": size}


def _roll_grid(roll_digits: int, roll_kind: str = "writein"):
    """
    Roll-number grid on page 1 only.
    N = roll_digits digit-columns × 10 rows (digits 0–9).
    Placed below the header band.

    Parameters
    ----------
    roll_digits : int   Number of digit columns.
    roll_kind   : str   "writein" | "prebubbled" | "none".
                        Stored in the descriptor as roll_grid.kind and
                        roll_grid.prefilled (True when kind == "prebubbled").
    """
    col_pitch = 22   # px between column centres
    row_pitch = 20   # px between row centres
    radius = ROLL_R

    # Grid starts below header band with a small gap
    origin_y = HEADER_H + 20  # top of first bubble row

    # Centre the grid horizontally in the left half of the page (column 0 area)
    # Left half: x in [MARGIN, W//2]
    grid_width = (roll_digits - 1) * col_pitch
    left_half_centre = MARGIN + (W // 2 - MARGIN) // 4  # ¼ of the way across
    origin_x = max(MARGIN + radius, left_half_centre - grid_width // 2)

    # Validate that all bubbles stay within the page
    max_cx = origin_x + (roll_digits - 1) * col_pitch + radius
    max_cy = origin_y + 9 * row_pitch + radius
    assert max_cx <= W, f"Roll grid exceeds page width: {max_cx} > {W}"
    assert max_cy <= H, f"Roll grid exceeds page height: {max_cy} > {H}"

    return {
        "origin": [origin_x, origin_y],
        "col_pitch": col_pitch,
        "row_pitch": row_pitch,
        "radius": radius,
        "cols": roll_digits,
        "rows": 10,
        "kind": roll_kind,
        "prefilled": (roll_kind == "prebubbled"),
    }


def _answer_grid(num_questions: int, num_options: int, page_count: int):
    """
    Build answer_bubbles list and page_map.

    Layout per page:
        - 2 columns; each column = ANSWER_ROWS_PER_COL rows (25).
        - For question index i across all pages:
              page   = i // ANSWERS_PER_PAGE
              j      = i % ANSWERS_PER_PAGE          (within-page index, 0–49)
              col    = j // ANSWER_ROWS_PER_COL      (0 or 1)
              row    = j % ANSWER_ROWS_PER_COL       (0–24)

    Column x origins:  col 0 centred in left half, col 1 in right half.
    Row y origin: below roll-grid area (page 1) or below a small top margin.
    """
    # Horizontal layout for the two answer columns
    # Column widths: each column occupies half the usable width
    usable_w = W - 2 * MARGIN
    half_w = usable_w // 2

    # For each column, the question-number label + num_options bubbles must fit
    # Label width ≈ 20 px, then num_options bubbles
    q_label_w = 22   # reserved for "Q01" label
    bubbles_w = num_options * OPTION_PITCH  # total width of option row

    row_block_w = q_label_w + bubbles_w

    # Column 0 left edge
    col0_left = MARGIN
    # Column 1 left edge
    col1_left = MARGIN + half_w

    # First option bubble centre for each column
    col_option_start = [
        col0_left + q_label_w + R,
        col1_left + q_label_w + R,
    ]

    # Vertical layout
    # Page 1: answer rows start below header + roll grid
    # Other pages: start just below top margin
    roll_grid_bottom = HEADER_H + 20 + 9 * 20 + ROLL_R + 10  # approx

    answer_top_page0 = roll_grid_bottom + 20   # page 1
    answer_top_other = MARGIN + FID + 15       # other pages (below top fiducials)

    row_pitch = (H - answer_top_page0 - MARGIN) // ANSWER_ROWS_PER_COL
    # Use a consistent row_pitch that fits even on page 1
    row_pitch_other = (H - answer_top_other - MARGIN) // ANSWER_ROWS_PER_COL
    # For safety, use the smaller (more constrained page 1) pitch everywhere
    row_pitch = min(row_pitch, row_pitch_other)
    # Ensure bubbles don't overlap
    row_pitch = max(row_pitch, 2 * R + 4)

    answer_bubbles = []
    page_map = {p: [] for p in range(page_count)}

    for i in range(num_questions):
        page = i // ANSWERS_PER_PAGE
        j = i % ANSWERS_PER_PAGE
        col = j // ANSWER_ROWS_PER_COL
        row = j % ANSWER_ROWS_PER_COL

        # y centre of this row's bubbles
        if page == 0:
            cy = answer_top_page0 + row * row_pitch
        else:
            cy = answer_top_other + row * row_pitch

        # x start for options in this column
        opt_start_x = col_option_start[col]

        options = []
        for opt_idx in range(num_options):
            label = chr(ord("A") + opt_idx)
            cx = opt_start_x + opt_idx * OPTION_PITCH
            options.append({"label": label, "cx": cx, "cy": cy, "r": R})

        entry = {"q_pos": i, "page": page, "options": options}
        answer_bubbles.append(entry)
        page_map[page].append(i)

    return answer_bubbles, page_map
