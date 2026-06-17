"""
omr.scan.read — Fill-ratio + hysteresis bubble reader.

Reads roll-number and answer bubbles from a warped canonical grayscale image
(827×1169, the output of warp_to_canonical or simulate_scan at scale=1.0).

Algorithm
---------
1. ``to_binary``   : Otsu inverse-threshold → ink=255, paper=0.
2. ``bubble_fill_ratio`` : sample a circular inner mask (radius*0.6) to avoid
   the printed outline ring; return ink-pixel fraction.
3. ``classify``    : hysteresis with FILL_HIGH / FILL_LOW thresholds.
4. ``read_roll``   : per digit-column, find which row digit is "filled".
5. ``read_answers``: per question, classify every option; flag double-marks
   and ambiguous (faint) reads.
"""

from __future__ import annotations

import cv2
import numpy as np

# ---------------------------------------------------------------------------
# Module constants — hysteresis thresholds
# ---------------------------------------------------------------------------
FILL_HIGH: float = 0.45   # ≥ this → "filled"
FILL_LOW: float  = 0.20   # ≤ this → "empty"; between the two → "ambiguous"


# ---------------------------------------------------------------------------
# Step 1 — Binarisation
# ---------------------------------------------------------------------------

def to_binary(canonical_gray: np.ndarray) -> np.ndarray:
    """
    Otsu inverse-threshold a canonical grayscale image.

    Returns a binary uint8 array where ink pixels = 255 and paper pixels = 0.

    Parameters
    ----------
    canonical_gray : np.ndarray
        uint8 grayscale array (H, W) — white background, dark ink.

    Returns
    -------
    np.ndarray  uint8 (H, W), ink=255, paper=0.
    """
    _, binary = cv2.threshold(
        canonical_gray,
        0, 255,
        cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU,
    )
    return binary


# ---------------------------------------------------------------------------
# Step 2 — Fill-ratio measurement
# ---------------------------------------------------------------------------

def bubble_fill_ratio(
    binary: np.ndarray,
    cx: float,
    cy: float,
    r: float,
) -> float:
    """
    Measure the ink fill ratio inside the *inner* disc of a bubble.

    We sample a disc of radius ``r * 0.6`` centred at ``(cx, cy)`` to
    ignore the printed outline ring (which sits at radius ``r``).

    Parameters
    ----------
    binary : np.ndarray
        uint8 binary image, ink=255.
    cx, cy : float
        Bubble centre in pixel coordinates.
    r : float
        Canonical bubble radius (from descriptor).

    Returns
    -------
    float  Fraction of ink pixels inside the inner disc, in [0.0, 1.0].
    """
    # Inner disc avoids the printed ring around the bubble
    inner_r = r * 0.6

    H, W = binary.shape
    icx = int(round(cx))
    icy = int(round(cy))
    ir  = int(math.ceil(inner_r))   # bounding half-extent for the patch

    # Build coordinate grids relative to centre
    y_lo = max(0, icy - ir)
    y_hi = min(H, icy + ir + 1)
    x_lo = max(0, icx - ir)
    x_hi = min(W, icx + ir + 1)

    if y_hi <= y_lo or x_hi <= x_lo:
        return 0.0

    # Create a sub-image of the patch
    patch = binary[y_lo:y_hi, x_lo:x_hi]

    # Build circular mask in patch coordinates
    ys = np.arange(y_lo, y_hi) - icy
    xs = np.arange(x_lo, x_hi) - icx
    xx, yy = np.meshgrid(xs, ys)
    mask = (xx ** 2 + yy ** 2) <= inner_r ** 2

    mask_count = int(mask.sum())
    if mask_count == 0:
        return 0.0

    ink_count = int((patch[mask] > 0).sum())
    return ink_count / mask_count


# math is needed for ceil — import at module level
import math


# ---------------------------------------------------------------------------
# Step 3 — Hysteresis classifier
# ---------------------------------------------------------------------------

def classify(ratio: float) -> str:
    """
    Classify a fill ratio with hysteresis.

    Returns
    -------
    "filled"    if ratio >= FILL_HIGH
    "empty"     if ratio <= FILL_LOW
    "ambiguous" otherwise
    """
    if ratio >= FILL_HIGH:
        return "filled"
    if ratio <= FILL_LOW:
        return "empty"
    return "ambiguous"


# ---------------------------------------------------------------------------
# Step 4 — Roll number reader
# ---------------------------------------------------------------------------

def read_roll(
    binary: np.ndarray,
    descriptor: dict,
) -> tuple[str, str | None]:
    """
    Read the roll number from the roll-grid on page 0.

    For each digit column, finds the row (0–9) whose bubble is classified
    "filled".  Assembles the digit string.  If any column has zero or more
    than one filled bubble, or any ambiguous bubble, the flag is set to
    ``"roll_unreadable"``.

    Parameters
    ----------
    binary : np.ndarray
        uint8 binary image (ink=255).
    descriptor : dict
        Canonical descriptor from omr.geometry.build_template().

    Returns
    -------
    (roll_str, flag)
        roll_str : str — best-effort digit string (one char per column;
                   '?' substituted for unreadable columns).
        flag     : "roll_unreadable" if any column is ambiguous or has ≠ 1
                   filled bubble; None otherwise.
    """
    rg = descriptor["roll_grid"]
    ox, oy = rg["origin"]
    col_pitch = rg["col_pitch"]
    row_pitch = rg["row_pitch"]
    radius    = rg["radius"]
    cols      = rg["cols"]
    rows      = rg["rows"]  # always 10

    digits: list[str] = []
    flag: str | None = None

    for col in range(cols):
        cx = ox + col * col_pitch
        filled_rows: list[int] = []
        has_ambiguous = False

        for row in range(rows):
            cy = oy + row * row_pitch
            ratio = bubble_fill_ratio(binary, cx, cy, radius)
            state = classify(ratio)

            if state == "filled":
                filled_rows.append(row)
            elif state == "ambiguous":
                has_ambiguous = True

        if has_ambiguous or len(filled_rows) != 1:
            flag = "roll_unreadable"
            if filled_rows:
                digits.append(str(filled_rows[0]))  # best-effort: first filled
            else:
                digits.append("?")
        else:
            digits.append(str(filled_rows[0]))

    roll_str = "".join(digits)
    return roll_str, flag


# ---------------------------------------------------------------------------
# Step 5 — Answer reader
# ---------------------------------------------------------------------------

def read_answers(
    binary: np.ndarray,
    descriptor: dict,
    page: int,
    multiple_allowed: bool = False,
) -> dict:
    """
    Read answer bubbles for all questions on *page*.

    Parameters
    ----------
    binary : np.ndarray
        uint8 binary image (ink=255), in canonical space.
    descriptor : dict
        Canonical descriptor from omr.geometry.build_template().
    page : int
        0-based page index.  Only questions assigned to this page are read.
    multiple_allowed : bool
        When False (default), marking two or more options on a single question
        sets the flag ``"double_mark"``.

    Returns
    -------
    dict  {q_pos (int): {"marked": [labels], "flag": str | None}}

    Flags
    -----
    "double_mark" : 2+ options filled when ``not multiple_allowed``
    "faint"       : at least one option is ambiguous
    (none)        : blank answer or clean single fill
    """
    result: dict[int, dict] = {}

    for entry in descriptor["answer_bubbles"]:
        if entry["page"] != page:
            continue

        q_pos   = entry["q_pos"]
        options = entry["options"]

        marked: list[str] = []
        faint = False

        for opt in options:
            ratio = bubble_fill_ratio(binary, opt["cx"], opt["cy"], opt["r"])
            state = classify(ratio)

            if state == "filled":
                marked.append(opt["label"])
            elif state == "ambiguous":
                faint = True

        # Determine flag
        flag: str | None = None
        if len(marked) >= 2 and not multiple_allowed:
            flag = "double_mark"
        elif faint:
            flag = "faint"

        result[q_pos] = {"marked": marked, "flag": flag}

    return result
