"""
omr.scan.read — measure how dark each bubble is and decide what was marked.

Works on the warped canonical grayscale image (827x1169), the output of
warp_to_canonical.

Why this does not binarise first
--------------------------------
The reader used to Otsu-threshold the page and then count black pixels inside
each bubble. Otsu picks ONE global cut, so a uniformly shaded mark falls
entirely on one side of it: an HB pencil bubble either survives whole (ratio
near 1.0) or vanishes whole (ratio near 0.0). The 0.20 to 0.45 "ambiguous" band
that is supposed to route uncertain marks to a human is therefore unreachable
for exactly the marks it exists to catch.

Measured on the benchmark corpus before this change: light pencil scored 14%
with 36 answers wrong AND unflagged, and fainter pencil scored 0% with 66 wrong
and unflagged, every one of them reported at full confidence. A student who
answered correctly in pencil was handed a zero and the product called the sheet
clean.

So measure greyness, not pixel counts, and measure it against references taken
from the same page:

    paper    median of an annulus just outside each bubble's printed ring, so
             local shading and paper tone cancel per bubble
    ink      taken from the fiducial squares, guaranteed solid print on this
             page, so exposure and white balance cancel globally

    darkness = (paper - bubble_interior) / (paper - ink)

That is 0 for untouched paper and 1 for a mark as dark as the printing, on any
exposure. A decision then needs both an absolute floor and a margin over the
runner-up, because a real sheet's wrong answer is not blank paper, it is an
erased or brushed bubble.
"""

from __future__ import annotations

import math

import cv2
import numpy as np

# ---------------------------------------------------------------------------
# Decision thresholds, in normalised darkness (0 = paper, 1 = as dark as print)
# ---------------------------------------------------------------------------

# Calibrated from measured distributions on the benchmark corpus, AFTER the
# per-label baseline removes the printed option letter. Across every capture
# condition, untouched bubbles sit at or below 0.037 (99th percentile, worst
# case) while the faintest real pencil mark starts at 0.145. These sit in that
# gap with roughly 3x headroom on each side.
#
# They are far lower than the old 0.45/0.20 pair because they measure a
# different thing: normalised greyness above the page's own blank level, not a
# fraction of post-threshold black pixels. Do not tune them by eye. Re-derive
# them with `manage.py scan_bench` if the sheet design changes.

# At or above this a mark is deliberate.
FILL_HIGH: float = 0.11
# At or below this the bubble is untouched.
FILL_LOW: float = 0.05
# The winner must beat the runner-up by this much, otherwise the question is
# ambiguous. Two similar marks mean the student changed their mind, and that is
# a decision for a human, not for a threshold.
MARGIN_MIN: float = 0.06


def to_binary(canonical_gray: np.ndarray) -> np.ndarray:
    """
    Otsu inverse-threshold, ink=255.

    Retained because callers outside the reader still want a binary view (the
    roll grid cross-check and debug overlays). It is NO LONGER the basis of any
    fill measurement.
    """
    _, binary = cv2.threshold(
        canonical_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )
    return binary


# ---------------------------------------------------------------------------
# Per-page references
# ---------------------------------------------------------------------------

def page_ink_level(canonical: np.ndarray, descriptor: dict) -> float:
    """
    How dark solid print is on THIS page, from the four fiducial squares.

    They are the only marks guaranteed to be present, solid, and printed by us,
    so they calibrate exposure without assuming the page is well lit. A dim
    photo simply has a brighter ink level and the ratio still lands correctly.
    """
    h, w = canonical.shape[:2]
    samples = []
    for f in descriptor.get("fiducials", []):
        cx, cy = int(f["cx"]), int(f["cy"])
        r = 6
        x0, y0 = max(0, cx - r), max(0, cy - r)
        x1, y1 = min(w, cx + r + 1), min(h, cy + r + 1)
        if x1 > x0 and y1 > y0:
            samples.append(canonical[y0:y1, x0:x1].reshape(-1))
    if not samples:
        return 40.0
    allpix = np.concatenate(samples)
    # 25th percentile, not the minimum: robust to a dead pixel or JPEG ringing.
    return float(np.percentile(allpix, 25))


def bubble_darkness(
    canonical: np.ndarray,
    cx: float,
    cy: float,
    r: float,
    ink_level: float,
) -> float:
    """
    Normalised darkness of one bubble, 0 for untouched paper, 1 for print-dark.

    The interior disc is sampled inside the printed ring; paper is sampled from
    an annulus just outside it, so uneven lighting cancels per bubble rather
    than per page.
    """
    h, w = canonical.shape[:2]
    icx, icy = int(round(cx)), int(round(cy))
    inner_r = r * 0.62
    outer_lo, outer_hi = r * 1.45, r * 2.15

    pad = int(math.ceil(outer_hi)) + 1
    y0, y1 = max(0, icy - pad), min(h, icy + pad + 1)
    x0, x1 = max(0, icx - pad), min(w, icx + pad + 1)
    if y1 <= y0 or x1 <= x0:
        return 0.0

    patch = canonical[y0:y1, x0:x1].astype(np.float32)
    ys = np.arange(y0, y1) - cy
    xs = np.arange(x0, x1) - cx
    xx, yy = np.meshgrid(xs, ys)
    d2 = xx * xx + yy * yy

    inner = patch[d2 <= inner_r * inner_r]
    ring = patch[(d2 >= outer_lo * outer_lo) & (d2 <= outer_hi * outer_hi)]
    if inner.size == 0:
        return 0.0

    # Median paper, so a neighbouring bubble clipped by the annulus cannot drag
    # the reference dark and inflate every reading on the row.
    paper = float(np.median(ring)) if ring.size else float(np.percentile(patch, 90))

    span = paper - ink_level
    if span < 25.0:
        # Page and print are nearly the same brightness: too washed out to
        # measure honestly. Report nothing rather than guess.
        return 0.0

    # Mean of the darkest 60% of the interior. A tick or a cross covers only
    # part of the disc, so a plain mean reads it as blank; taking the darker
    # tail finds the stroke while still ignoring the odd speck.
    k = max(1, int(inner.size * 0.60))
    darkest = np.partition(inner, k - 1)[:k]
    level = float(darkest.mean())

    return float(np.clip((paper - level) / span, 0.0, 1.0))


def _normalise_against_blanks(raw: dict, baseline: float) -> dict:
    """
    Rescale so an untouched bubble reads 0 and a solid mark reads 1.

    Every bubble has the option letter printed INSIDE it (generator.py draws
    the label centred on the circle), so an untouched bubble is not blank
    paper: measured, it sits around 0.20 darkness, right on the "empty"
    threshold. That is why clean sheets produced a run of spurious faint flags.

    Subtracting a baseline taken from the page's own untouched bubbles removes
    the printed glyph, the paper tone and the exposure in one step, and it does
    so for sheets that are ALREADY PRINTED, which moving the letter out of the
    circle would not.
    """
    span = max(1e-6, 1.0 - baseline)
    return {k: float(np.clip((v - baseline) / span, 0.0, 1.0)) for k, v in raw.items()}


def _blank_baseline(values: list[float]) -> float:
    """
    Estimate the untouched-bubble level from a group that is mostly untouched.

    With four options and one answer, three quarters of every group is blank,
    so a low percentile is a robust reading of "printed but unmarked". The 40th
    is used rather than the median to stay clear even when a student marks two.
    """
    if not values:
        return 0.0
    return float(min(np.percentile(values, 40), 0.35))


def _ring_template(r: float) -> np.ndarray:
    """A synthetic printed bubble outline, used to find where the real one is."""
    size = int(round(r * 2)) * 2 + 1
    t = np.full((size, size), 255, dtype=np.uint8)
    c = size // 2
    cv2.circle(t, (c, c), int(round(r)), 0, 1, lineType=cv2.LINE_AA)
    return t


def registration_score(canonical: np.ndarray, descriptor: dict, page: int = 0) -> float:
    """
    How closely the rectified page lines up with the template, 0 to 1.

    Aligning the four fiducials proves the CORNERS match. It does not prove the
    middle does. A creased or curled sheet is not planar, so no single
    homography can rectify it: the corners land perfectly while bubbles toward
    the centre drift by several pixels. Nothing noticed, and a folded sheet was
    graded confidently against the wrong bubbles, 52 answers wrong and
    unflagged on the benchmark. That is the worst failure this product can
    produce, because the teacher has no signal that anything went wrong.

    Every bubble is printed as a ring at a known position, which makes them a
    dense, page-wide registration target we already pay to print. This locates
    the real ring near each expected centre and measures how far it moved.
    Presence is not enough: a drifted grid still has rings, just not where the
    coordinates say. Only the DISPLACEMENT distinguishes a good rectification
    from a plausible but wrong one.
    """
    entries = [e for e in descriptor.get("answer_bubbles", []) if e["page"] == page]
    if not entries:
        return 1.0

    # Spread the sample: distortion is worst away from the corners the warp was
    # fitted to, so a clustered sample would miss exactly what this looks for.
    step = max(1, len(entries) // 14)
    sample = entries[::step]
    if not sample:
        return 1.0

    h, w = canonical.shape[:2]
    r = float(sample[0]["options"][0]["r"])
    tmpl = _ring_template(r)
    search = int(round(r * 1.4))          # how far we will look for the ring
    half = tmpl.shape[0] // 2
    pad = half + search

    good = 0
    total = 0
    for e in sample:
        opt = e["options"][0]
        cx, cy = int(round(opt["cx"])), int(round(opt["cy"]))
        y0, y1 = cy - pad, cy + pad + 1
        x0, x1 = cx - pad, cx + pad + 1
        if y0 < 0 or x0 < 0 or y1 > h or x1 > w:
            continue
        window = canonical[y0:y1, x0:x1]
        if window.shape[0] < tmpl.shape[0] or window.shape[1] < tmpl.shape[1]:
            continue
        res = cv2.matchTemplate(window, tmpl, cv2.TM_CCOEFF_NORMED)
        _minv, maxv, _minl, maxl = cv2.minMaxLoc(res)
        total += 1
        # Where the best match sits relative to the expected centre.
        dx = maxl[0] - search
        dy = maxl[1] - search
        if maxv > 0.25 and (dx * dx + dy * dy) <= 4.0:   # within 2 px
            good += 1

    return good / total if total else 1.0


def classify(ratio: float) -> str:
    """"filled" above FILL_HIGH, "empty" below FILL_LOW, "ambiguous" between."""
    if ratio >= FILL_HIGH:
        return "filled"
    if ratio <= FILL_LOW:
        return "empty"
    return "ambiguous"


# ---------------------------------------------------------------------------
# Backwards-compatible shim
# ---------------------------------------------------------------------------

def bubble_fill_ratio(image: np.ndarray, cx: float, cy: float, r: float) -> float:
    """
    Fraction of ink pixels in the inner disc of a bubble.

    Kept for callers that already hold a BINARY image (ink=255). New code
    should use bubble_darkness on the grayscale page instead: this cannot
    distinguish a faint mark from a blank one, because binarisation has already
    thrown that information away.
    """
    inner_r = r * 0.6
    h, w = image.shape[:2]
    icx, icy = int(round(cx)), int(round(cy))
    ir = int(math.ceil(inner_r))

    y0, y1 = max(0, icy - ir), min(h, icy + ir + 1)
    x0, x1 = max(0, icx - ir), min(w, icx + ir + 1)
    if y1 <= y0 or x1 <= x0:
        return 0.0

    patch = image[y0:y1, x0:x1]
    ys = np.arange(y0, y1) - icy
    xs = np.arange(x0, x1) - icx
    xx, yy = np.meshgrid(xs, ys)
    mask = (xx ** 2 + yy ** 2) <= inner_r ** 2
    if not mask.any():
        return 0.0
    return float((patch[mask] > 0).sum()) / float(mask.sum())


# ---------------------------------------------------------------------------
# Roll number
# ---------------------------------------------------------------------------

def read_roll(canonical: np.ndarray, descriptor: dict) -> tuple[str, str | None]:
    """
    Read the roll grid on page 0.

    Per column, the darkest digit wins only if it clears the fill threshold and
    beats the runner-up by MARGIN_MIN. Anything else flags roll_unreadable
    rather than guessing an identity, because attaching a sheet to the wrong
    student is worse than asking.
    """
    rg = descriptor["roll_grid"]
    ox, oy = rg["origin"]
    col_pitch, row_pitch = rg["col_pitch"], rg["row_pitch"]
    radius, cols, rows = rg["radius"], rg["cols"], rg["rows"]

    ink = page_ink_level(canonical, descriptor)

    # Same correction as the answer grid: each roll bubble has its digit printed
    # inside it, so "untouched" is not zero. Baseline per ROW, because every
    # bubble in a row carries the same glyph and at most one column is marked.
    raw = [[bubble_darkness(canonical, ox + c * col_pitch, oy + r * row_pitch, radius, ink)
            for c in range(cols)] for r in range(rows)]
    row_base = [_blank_baseline(row_vals) for row_vals in raw]

    digits: list[str] = []
    flag: str | None = None

    for col in range(cols):
        cx = ox + col * col_pitch
        vals = [
            _normalise_against_blanks({"v": raw[row][col]}, row_base[row])["v"]
            for row in range(rows)
        ]
        order = np.argsort(vals)[::-1]
        best, second = int(order[0]), int(order[1]) if rows > 1 else None
        top = vals[best]
        runner = vals[second] if second is not None else 0.0

        if top >= FILL_HIGH and (top - runner) >= MARGIN_MIN:
            digits.append(str(best))
        else:
            flag = "roll_unreadable"
            digits.append(str(best) if top >= FILL_HIGH else "?")

    return "".join(digits), flag


# ---------------------------------------------------------------------------
# Answers
# ---------------------------------------------------------------------------

def read_answers(
    canonical: np.ndarray,
    descriptor: dict,
    page: int,
    multiple_allowed: bool = False,
    ink_level: float | None = None,
) -> dict:
    """
    Read every answer bubble on *page* from the canonical GRAYSCALE image.

    Returns ``{q_pos: {"marked": [...], "flag": str|None, "darkness": {...},
    "margin": float}}``.

    ``margin`` is how far the decision was from being a different decision, and
    it is what makes the sheet's confidence score mean something. Previously
    confidence was the fraction of unflagged questions, which is 1.0 precisely
    when nothing was flagged, including on a page read entirely wrong.

    Flags
    -----
    ``double_mark``  two or more options clearly filled
    ``faint``        something is there but not clearly enough to score
    """
    if ink_level is None:
        ink_level = page_ink_level(canonical, descriptor)

    entries = [e for e in descriptor["answer_bubbles"] if e["page"] == page]

    # One pass to learn what an UNMARKED bubble of each option letter looks like
    # on this page, then a second to decide. Per label rather than per page,
    # because "A" and "D" print different amounts of ink inside the circle.
    raw_by_label: dict[str, list[float]] = {}
    for e in entries:
        for opt in e["options"]:
            raw_by_label.setdefault(opt["label"], []).append(
                bubble_darkness(canonical, opt["cx"], opt["cy"], opt["r"], ink_level)
            )
    baselines = {lbl: _blank_baseline(vals) for lbl, vals in raw_by_label.items()}

    result: dict[int, dict] = {}

    for entry in descriptor["answer_bubbles"]:
        if entry["page"] != page:
            continue

        q_pos = entry["q_pos"]
        options = entry["options"]

        darkness = {
            opt["label"]: _normalise_against_blanks(
                {opt["label"]: bubble_darkness(
                    canonical, opt["cx"], opt["cy"], opt["r"], ink_level)},
                baselines.get(opt["label"], 0.0),
            )[opt["label"]]
            for opt in options
        }
        if not darkness:
            result[q_pos] = {"marked": [], "flag": None, "darkness": {}, "margin": 1.0}
            continue

        ranked = sorted(darkness.items(), key=lambda kv: kv[1], reverse=True)
        top_label, top_val = ranked[0]
        runner_val = ranked[1][1] if len(ranked) > 1 else 0.0

        filled = [lbl for lbl, v in darkness.items() if v >= FILL_HIGH]
        marked: list[str] = []
        flag: str | None = None

        if len(filled) >= 2 and not multiple_allowed:
            marked = sorted(filled)
            flag = "double_mark"
            # Distance from the second mark falling below the threshold.
            margin = abs(sorted(darkness.values(), reverse=True)[1] - FILL_HIGH)
        elif multiple_allowed and filled:
            marked = sorted(filled)
            margin = min(abs(darkness[l] - FILL_HIGH) for l in filled)
        elif top_val >= FILL_HIGH and (top_val - runner_val) >= MARGIN_MIN:
            marked = [top_label]
            margin = min(top_val - FILL_HIGH, top_val - runner_val - MARGIN_MIN + 0.15)
        elif top_val <= FILL_LOW:
            marked = []          # genuinely blank
            margin = FILL_LOW - top_val
        else:
            # Something is on the paper but it is not a confident answer: a
            # light pencil, an erasure, or two marks of similar weight. This is
            # the case the old reader could not represent at all.
            marked = []
            flag = "faint"
            margin = 0.0

        result[q_pos] = {
            "marked": marked,
            "flag": flag,
            "darkness": {k: round(v, 4) for k, v in darkness.items()},
            "margin": round(float(max(0.0, margin)), 4),
        }

    return result
