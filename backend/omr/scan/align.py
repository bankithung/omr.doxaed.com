"""
omr.scan.align — locate the sheet in a photograph and rectify it.

Pipeline
--------
    1. crop_to_page       crop the frame down to the sheet itself
    2. decode_qr          read "sheet_code|page|total", escalating on failure
    3. detect_fiducials   find the four corner squares on the page
    4. warp_to_canonical  rectify to the 827x1169 canonical space

Why the page is cropped first
-----------------------------
This module used to run a global Otsu threshold over the whole frame to find
the fiducials. That works only when the frame is entirely paper. The moment a
photograph includes the desk, Otsu's two populations become PAPER and DESK
rather than INK and PAPER, the whole sheet becomes one solid blob, and all four
fiducials dissolve into it. Measured on the benchmark corpus before this
change: a page on a white table read 100%, on a wooden table 0%, on a dark mat
0%, and at any handheld angle 0%.

Cropping to the page first makes the histogram ink versus paper again, and it
supplies the perspective correction the old code did not do at all, so every
handheld photo was previously read off a keystoned grid.

Illumination
------------
Shadows, lens vignetting and underexposure are all slowly varying gains; ink is
a fast variation. Dividing by a heavily blurred copy removes the former and
keeps the latter, so one flat-field pass covers all three instead of needing a
special case each.
"""

from __future__ import annotations

import cv2
import numpy as np
from pyzbar.pyzbar import decode as pyzbar_decode


# Long edge used for page and fiducial search. Detection does not need full
# resolution and its cost is quadratic in pixels, so this is most of the
# latency budget.
DETECT_LONG_EDGE = 1100

# Paper level after flat-fielding. Mid grey leaves headroom in both directions.
FLAT_PAPER = 160


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _as_gray(image: np.ndarray) -> np.ndarray:
    if image is None:
        raise ValueError("image is None")
    if image.ndim == 2:
        return image
    if image.shape[2] == 4:
        return cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def _odd(n) -> int:
    n = int(max(3, n))
    return n if n % 2 == 1 else n + 1


def flatten_illumination(gray: np.ndarray, sigma_frac: float = 0.08) -> np.ndarray:
    """
    Divide out the illumination field so paper reads the same everywhere.

    A shadow across the page, lens falloff and plain underexposure are all
    multiplicative and low frequency. Estimating that field with a large blur
    and dividing it out normalises paper to a constant, so one threshold works
    across the whole sheet. Ink survives because it is far smaller than the
    blur radius.
    """
    h, w = gray.shape[:2]
    k = _odd(int(max(h, w) * sigma_frac))
    bg = cv2.GaussianBlur(gray, (k, k), 0).astype(np.float32)
    out = (gray.astype(np.float32) + 1.0) / (bg + 1.0) * FLAT_PAPER
    return np.clip(out, 0, 255).astype(np.uint8)


def _order_quad(pts: np.ndarray) -> np.ndarray:
    """Order 4 points TL, TR, BR, BL from coordinate sums and differences."""
    pts = np.asarray(pts, dtype=np.float32).reshape(4, 2)
    s = pts.sum(axis=1)
    d = (pts[:, 1] - pts[:, 0])
    return np.array([
        pts[np.argmin(s)],   # TL, smallest x+y
        pts[np.argmin(d)],   # TR, smallest y-x
        pts[np.argmax(s)],   # BR, largest x+y
        pts[np.argmax(d)],   # BL, largest y-x
    ], dtype=np.float32)


# ---------------------------------------------------------------------------
# Stage 1 — page localisation
# ---------------------------------------------------------------------------

def locate_page(gray: np.ndarray, aspect: float | None = None) -> np.ndarray | None:
    """
    Return the sheet's four corners in *gray* coordinates as TL, TR, BR, BL,
    or None when the frame already is the page (or no plausible quad exists).

    Runs on a downscaled copy: a page boundary is a huge feature, so resolution
    buys nothing here and costs a great deal.
    """
    h, w = gray.shape[:2]
    scale = DETECT_LONG_EDGE / float(max(h, w))
    if scale < 1.0:
        small = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    else:
        small, scale = gray, 1.0
    sh, sw = small.shape[:2]
    frame_area = float(sh * sw)

    blurred = cv2.GaussianBlur(small, (5, 5), 0)

    # Two views of "where does the paper end". Otsu is decisive when the desk is
    # clearly darker. Canny still finds the border when the contrast is slight,
    # which is the white page on a white table that Otsu cannot separate at all.
    _, otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    edges = cv2.dilate(cv2.Canny(blurred, 40, 120), np.ones((3, 3), np.uint8), 1)

    quads: list[tuple[float, np.ndarray]] = []
    for mask in (otsu, edges):
        closed = cv2.morphologyEx(
            mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
        )
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in sorted(contours, key=cv2.contourArea, reverse=True)[:5]:
            area = cv2.contourArea(cnt)
            # Big enough to be the page, but not the entire frame: if it fills
            # the frame there is no visible desk and cropping is a no-op.
            if area < frame_area * 0.20 or area > frame_area * 0.985:
                continue
            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
            if len(approx) == 4 and cv2.isContourConvex(approx):
                quads.append((area, approx.reshape(4, 2).astype(np.float32)))
            else:
                # A torn or occluded edge will not reduce to four points; the
                # minimum area rectangle still recovers the page.
                box = cv2.boxPoints(cv2.minAreaRect(cnt)).astype(np.float32)
                if cv2.contourArea(box) >= frame_area * 0.20:
                    quads.append((area * 0.9, box))

    if not quads:
        return None

    def shape_score(item):
        a, q = item
        o = _order_quad(q)
        wid = (np.linalg.norm(o[1] - o[0]) + np.linalg.norm(o[2] - o[3])) / 2.0
        hei = (np.linalg.norm(o[3] - o[0]) + np.linalg.norm(o[2] - o[1])) / 2.0
        if wid < 1 or hei < 1:
            return -1.0
        if not aspect:
            return a / frame_area
        err = abs((wid / hei) - aspect) / aspect
        # Prefer a quad shaped like the sheet over one that is merely large: a
        # dark table edge can easily be bigger than the page.
        return (a / frame_area) * max(0.0, 1.0 - min(err, 1.0))

    quads.sort(key=shape_score, reverse=True)
    if shape_score(quads[0]) <= 0.0:
        return None
    return _order_quad(quads[0][1]) / scale


def crop_to_page(gray: np.ndarray, descriptor: dict) -> np.ndarray:
    """
    Rectify the frame down to the sheet, upright.

    Returns the image unchanged when no page boundary is visible, which is the
    flatbed case where paper already fills the frame.
    """
    W_canon, H_canon = descriptor["page_px"]
    aspect = float(W_canon) / float(H_canon)
    quad = locate_page(gray, aspect=aspect)
    if quad is None:
        return gray

    wid = max(np.linalg.norm(quad[1] - quad[0]), np.linalg.norm(quad[2] - quad[3]))
    hei = max(np.linalg.norm(quad[3] - quad[0]), np.linalg.norm(quad[2] - quad[1]))
    if wid < 80 or hei < 80:
        return gray

    # Rectify at roughly twice canonical: enough detail for the QR and the
    # fiducial edges, without paying for the camera's full resolution.
    out_w = int(round(min(max(wid, W_canon * 1.6), W_canon * 2.4)))
    out_h = int(round(out_w / aspect))
    dst = np.array([[0, 0], [out_w - 1, 0], [out_w - 1, out_h - 1], [0, out_h - 1]],
                   dtype=np.float32)
    M = cv2.getPerspectiveTransform(quad, dst)
    return cv2.warpPerspective(gray, M, (out_w, out_h),
                               flags=cv2.INTER_LINEAR, borderValue=255)


# ---------------------------------------------------------------------------
# Stage 2 — QR decode
# ---------------------------------------------------------------------------

def _parse_qr_payload(text: str):
    parts = text.split("|")
    if len(parts) != 3:
        return None
    try:
        return parts[0], int(parts[1]), int(parts[2])
    except ValueError:
        return None


def _try_decode(img: np.ndarray):
    try:
        codes = pyzbar_decode(img)
    except Exception:
        return None
    for code in codes:
        if code.type != "QRCODE":
            continue
        try:
            parsed = _parse_qr_payload(code.data.decode("utf-8"))
        except UnicodeDecodeError:
            continue
        if parsed:
            return parsed
    return None


def decode_qr_fast(image: np.ndarray) -> tuple[str, int, int] | None:
    """
    Two cheap attempts on the full frame. A clean capture succeeds here.

    Deliberately shallow: every further repair scales with the whole image, and
    on a multi-megapixel photo those steps cost over a second EACH while the
    aligned patch below does the same job on 80 px in a few milliseconds. Fail
    fast and let alignment take over.
    """
    gray = _as_gray(image)
    hit = _try_decode(gray)
    if hit:
        return hit
    return _try_decode(flatten_illumination(gray))


def decode_qr(image: np.ndarray) -> tuple[str, int, int] | None:
    """
    Full escalation ladder, cheapest first.

    Kept for callers that hold no template and therefore cannot align. Inside
    the pipeline, prefer decode_qr_fast then decode_qr_aligned: the expensive
    steps here scale with the whole frame, and on a blurred multi-megapixel
    capture they cost seconds and still fail.
    """
    gray = _as_gray(image)
    hit = decode_qr_fast(gray)
    if hit:
        return hit
    flat = flatten_illumination(gray)

    # Photographed from too far away: pyzbar needs a few pixels per module and
    # interpolation genuinely recovers them.
    h, w = gray.shape[:2]
    if max(h, w) < 2400:
        big = cv2.resize(flat, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        hit = _try_decode(big)
        if hit:
            return hit
        hit = _try_decode(
            cv2.threshold(big, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        )
        if hit:
            return hit

    # Unsharp mask, to undo mild defocus.
    sharp = cv2.addWeighted(flat, 1.8, cv2.GaussianBlur(flat, (0, 0), 3), -0.8, 0)
    hit = _try_decode(sharp)
    if hit:
        return hit

    # A different implementation with different failure modes.
    otsu = cv2.threshold(flat, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    for candidate in (flat, otsu):
        try:
            text, _pts, _ = cv2.QRCodeDetector().detectAndDecode(candidate)
        except cv2.error:
            continue
        if text:
            parsed = _parse_qr_payload(text)
            if parsed:
                return parsed

    return None


def _deblur(patch: np.ndarray, factor: int) -> np.ndarray:
    """Unsharp mask sized to the upscale, to undo defocus and mild smear."""
    return cv2.addWeighted(patch, 2.0, cv2.GaussianBlur(patch, (0, 0), factor), -1.0, 0)


def _qr_boxes(canonical: np.ndarray, descriptor: dict):
    """
    The two places the QR can be, most likely first.

    Four identical corner squares are rotationally symmetric, so an upside down
    sheet warps perfectly and the QR ends up in the opposite corner. Guessing
    which corner by ink coverage costs about a millisecond and halves the
    decode work, because the wrong corner is mostly blank paper and every
    expensive repair on it is wasted.
    """
    h, w = canonical.shape[:2]
    qr = descriptor["qr"]
    qx, qy, qs = int(qr["x"]), int(qr["y"]), int(qr["size"])
    pad = max(6, qs // 5)
    side = qs + 2 * pad

    def box(x0, y0, flipped):
        x0, y0 = max(0, int(x0)), max(0, int(y0))
        return (x0, y0, min(w, x0 + side), min(h, y0 + side), flipped)

    upright = box(qx - pad, qy - pad, False)
    flipped = box(w - qx - qs - pad, h - qy - qs - pad, True)

    def ink(b):
        x0, y0, x1, y1, _ = b
        if x1 <= x0 or y1 <= y0:
            return -1.0
        patch = canonical[y0:y1, x0:x1]
        return float((patch < max(60, int(patch.mean()) - 30)).mean())

    return [upright, flipped] if ink(upright) >= ink(flipped) else [flipped, upright]


def decode_qr_from_canonical(canonical: np.ndarray, descriptor: dict):
    """
    Read the QR from the position the template says it occupies on an already
    rectified page. Returns ``(payload, upside_down)`` or ``None``.

    Searching a multi-megapixel frame for an 80 px block fails on precisely the
    captures a phone produces, and fails slowly. Once the page is rectified the
    QR is a known square, so upscaling and deblurring just that patch is both
    far cheaper and far more likely to work: perspective is already gone and
    the whole interpolation budget goes into the modules that matter.

    Which corner it is found in doubles as the orientation test.

    Operating envelope, measured with `manage.py scan_bench`: the code reads
    reliably while a motion smear stays within about one module width (4.5 px
    at the current 112 px block), and fails beyond roughly 1.5. That limit is
    close to fundamental, since once the smear exceeds a module the adjacent
    modules merge and the information is gone. Wiener deconvolution along the
    estimated smear direction was tried and recovered nothing at any blur
    length while costing 2.5 s per sheet, so it was removed. Beyond the
    envelope the honest outcome is to refuse and ask for another photograph,
    which is what happens.
    """
    if not descriptor.get("qr"):
        return None

    for x0, y0, x1, y1, flipped in _qr_boxes(canonical, descriptor):
        if x1 - x0 < 24 or y1 - y0 < 24:
            continue
        patch = canonical[y0:y1, x0:x1]
        if flipped:
            patch = cv2.rotate(patch, cv2.ROTATE_180)

        # Cheapest first. A clean sheet decodes on the first try; the repairs
        # below only run for captures that need them.
        hit = _try_decode(patch)
        if hit:
            return hit, flipped

        # Upscale only as far as pyzbar needs. The block is 112 px across 25
        # modules, so x4 already gives ~18 px per module; x9 was 40 px per
        # module, four times the pixels to scan for no additional information.
        for factor in (4, 7):
            big = cv2.resize(patch, None, fx=factor, fy=factor,
                             interpolation=cv2.INTER_CUBIC)
            flat = flatten_illumination(big, sigma_frac=0.30)
            sharp = _deblur(flat, factor)
            for candidate in (
                cv2.threshold(sharp, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],
                flat,
            ):
                hit = _try_decode(candidate)
                if hit:
                    return hit, flipped

    return None


# ---------------------------------------------------------------------------
# Stage 3 — fiducial detection
# ---------------------------------------------------------------------------

def _fiducial_candidates(bin_img: np.ndarray, expected_side: float):
    """Return (cx, cy) for blobs shaped like a printed corner square."""
    contours, _ = cv2.findContours(bin_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    expected_area = expected_side ** 2
    lo, hi = expected_area * 0.25, expected_area * 4.0

    out = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < lo or area > hi:
            continue
        x, y, bw, bh = cv2.boundingRect(cnt)
        if bw < 3 or bh < 3:
            continue
        if abs(bw / bh - 1.0) > 0.45:
            continue
        # Solidity rejects hollow shapes. An answer bubble is a ring of similar
        # size to a fiducial; a loose filter lets one masquerade as a corner and
        # produce a believable, completely wrong warp.
        if area / float(bw * bh) < 0.80:
            continue
        M = cv2.moments(cnt)
        if M["m00"] == 0:
            continue
        out.append((M["m10"] / M["m00"], M["m01"] / M["m00"]))
    return out


def _validate_quad(tl, tr, br, bl, aspect: float) -> bool:
    """
    Reject a fiducial set whose geometry cannot be a rectangle in perspective.

    Without this, three real corners plus one stray blob produce a warp that
    looks plausible and grades an entire sheet wrong at high confidence.
    """
    top = float(np.linalg.norm(tr - tl))
    bottom = float(np.linalg.norm(br - bl))
    left = float(np.linalg.norm(bl - tl))
    right = float(np.linalg.norm(br - tr))
    if min(top, bottom, left, right) < 20:
        return False
    if max(top, bottom) / max(min(top, bottom), 1e-6) > 1.40:
        return False
    if max(left, right) / max(min(left, right), 1e-6) > 1.40:
        return False
    got = ((top + bottom) / 2.0) / max((left + right) / 2.0, 1e-6)
    return abs(got - aspect) / aspect <= 0.30


def detect_fiducials(image: np.ndarray, descriptor: dict) -> np.ndarray | None:
    """
    Locate the four corner squares, returning centroids as TL, TR, BL, BR.

    Works on a downscaled, flat-fielded copy and thresholds adaptively, so a
    shadow over one corner no longer erases it. Each candidate is matched to
    the corner it should belong to, then the quad is validated before anything
    is warped.
    """
    gray = _as_gray(image)
    h, w = gray.shape[:2]

    scale = DETECT_LONG_EDGE / float(max(h, w))
    if scale < 1.0:
        small = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    else:
        small, scale = gray, 1.0
    sh, sw = small.shape[:2]

    from omr.geometry import FID, W as CANON_W

    W_canon, H_canon = descriptor["page_px"]
    aspect = float(W_canon) / float(H_canon)
    expected_side = FID * (sw / float(CANON_W))

    flat = flatten_illumination(small, sigma_frac=0.10)

    block = _odd(expected_side * 6)
    masks = [
        # Adaptive first: the one that survives a gradient across the page.
        cv2.adaptiveThreshold(flat, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                              cv2.THRESH_BINARY_INV, block, 12),
        cv2.threshold(flat, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1],
        cv2.threshold(small, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1],
    ]

    corners = [(0.0, 0.0), (sw - 1.0, 0.0), (0.0, sh - 1.0), (sw - 1.0, sh - 1.0)]
    max_dist = 0.45 * float(np.hypot(sw, sh))

    for mask in masks:
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        cands = _fiducial_candidates(mask, expected_side)
        if len(cands) < 4:
            continue

        pts = np.array(cands, dtype=np.float32)
        chosen, used, ok = [], set(), True
        for cx, cy in corners:
            d = np.hypot(pts[:, 0] - cx, pts[:, 1] - cy)
            pick = None
            for idx in np.argsort(d):
                if int(idx) in used or d[idx] > max_dist:
                    continue
                pick = int(idx)
                break
            if pick is None:
                ok = False
                break
            used.add(pick)
            chosen.append(pts[pick])
        if not ok:
            continue

        tl, tr, bl, br = chosen
        if not _validate_quad(tl, tr, br, bl, aspect):
            continue
        return np.array([tl, tr, bl, br], dtype=np.float32) / scale

    return None


# ---------------------------------------------------------------------------
# Stage 4 — warp and orientation
# ---------------------------------------------------------------------------

def warp_to_canonical(image: np.ndarray, src_pts: np.ndarray, descriptor: dict) -> np.ndarray:
    """
    Rectify so the four fiducial centres land on their canonical positions.
    Output is exactly the descriptor's page size, so every downstream lookup is
    a plain coordinate read.
    """
    gray = _as_gray(image)
    W_canon, H_canon = descriptor["page_px"]
    dst_pts = np.array([[f["cx"], f["cy"]] for f in descriptor["fiducials"]],
                       dtype=np.float32)
    M = cv2.getPerspectiveTransform(src_pts.astype(np.float32), dst_pts)
    return cv2.warpPerspective(gray, M, (W_canon, H_canon),
                               flags=cv2.INTER_LINEAR, borderValue=255)


def is_upside_down(canonical: np.ndarray, descriptor: dict) -> bool:
    """
    True when the sheet was warped 180 degrees out.

    Four identical corner squares are rotationally symmetric, so an upside down
    sheet warps perfectly and then grades against mirrored bubble positions. On
    the benchmark that scored 0% while reporting high confidence, which is the
    worst failure this product can produce: a confident wrong number. The QR is
    the only asymmetric landmark on the page, so it is what tells us which way
    up we are.
    """
    qr = descriptor.get("qr")
    if not qr:
        return False
    h, w = canonical.shape[:2]
    qx, qy, qs = int(qr["x"]), int(qr["y"]), int(qr["size"])

    def ink_fraction(x0, y0, side):
        x0, y0 = max(0, int(x0)), max(0, int(y0))
        x1, y1 = min(w, x0 + side), min(h, y0 + side)
        if x1 <= x0 or y1 <= y0:
            return 0.0
        patch = canonical[y0:y1, x0:x1]
        thr = max(60, int(np.percentile(canonical, 60)) - 40)
        return float((patch < thr).mean())

    here = ink_fraction(qx, qy, qs)
    # Where the QR would land if the page were rotated 180 degrees.
    there = ink_fraction(w - qx - qs, h - qy - qs, qs)
    # A QR block is roughly half ink. Require a clear winner so a blank or
    # washed out page is never flipped on noise alone.
    return there > here + 0.10 and there > 0.15
