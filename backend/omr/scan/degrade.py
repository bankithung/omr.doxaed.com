"""
omr.scan.degrade — synthesise realistic capture damage for benchmarking.

The scan simulator produces an ideal render: pure black marks, even lighting,
no lens, no sensor, no desk. Real input is a phone photo of a printed page, and
every one of those differences is a way for the reader to be wrong.

Everything here is deterministic given a seed so a benchmark run is repeatable
and a regression is attributable.

Two families:

``mark_*``  how the STUDENT filled the bubble (grey pencil, off centre, a tick
            rather than a fill, a heavy biro that bleeds past the ring).
``cap_*``   how the CAMERA saw the page (defocus, motion, low light, a shadow
            across the sheet, keystone from holding the phone at an angle,
            sensor noise, JPEG, and the desk the page is lying on).

Marks have to be modelled separately from capture because they fail in opposite
directions: a faint mark must still be *found* (or flagged), while a heavy one
must not bleed into its neighbour.
"""

from __future__ import annotations

import cv2
import numpy as np


# ---------------------------------------------------------------------------
# Student marks
# ---------------------------------------------------------------------------

# Approximate 8-bit grey levels of real marks on white paper.
INK_HEAVY_BIRO = 25     # ballpoint, pressed hard
INK_BIRO = 60           # normal ballpoint
INK_PENCIL_HB = 110     # HB pencil, normal pressure
INK_PENCIL_LIGHT = 165  # HB pencil, barely touching. THE hard case.
INK_PENCIL_FAINT = 195  # almost invisible; must be flagged, never scored


def mark_bubble(
    img: np.ndarray,
    cx: float,
    cy: float,
    r: float,
    *,
    style: str = "fill",
    ink: int = INK_BIRO,
    coverage: float = 0.75,
    offset: tuple[float, float] = (0.0, 0.0),
    rng: np.random.Generator | None = None,
) -> None:
    """
    Draw one student mark in place.

    style
        ``fill``   the intended behaviour: a shaded disc.
        ``tick``   a check mark through the bubble. Covers little of the disc,
                   so a naive area ratio reads it as blank.
        ``cross``  two strokes through the centre.
        ``scribble`` back and forth strokes, uneven coverage.
        ``edge``   shaded but badly off centre, spilling over the printed ring.
    coverage
        Fraction of the bubble radius the mark spans, for ``fill``.
    ink
        Grey level of the mark. Lower is darker.
    """
    rng = rng or np.random.default_rng(0)
    cx += offset[0] * r
    cy += offset[1] * r
    icx, icy = int(round(cx)), int(round(cy))

    if style == "fill":
        rad = max(1, int(round(r * coverage)))
        # A real shaded bubble is not a uniform disc: pressure varies across
        # the stroke, so build it from overlapping soft dabs.
        layer = np.full(img.shape, 255, dtype=np.uint8)
        cv2.circle(layer, (icx, icy), rad, int(ink), -1)
        n_dabs = 6
        for _ in range(n_dabs):
            jx = icx + int(rng.integers(-max(1, rad // 3), max(2, rad // 3)))
            jy = icy + int(rng.integers(-max(1, rad // 3), max(2, rad // 3)))
            shade = int(np.clip(ink + rng.integers(-25, 26), 0, 255))
            cv2.circle(layer, (jx, jy), max(1, int(rad * 0.7)), shade, -1)
        layer = cv2.GaussianBlur(layer, (3, 3), 0)
        np.minimum(img, layer, out=img)
        return

    thickness = max(1, int(round(r * 0.35)))
    if style == "tick":
        pts = [
            (icx - int(r * 0.6), icy),
            (icx - int(r * 0.1), icy + int(r * 0.55)),
            (icx + int(r * 0.8), icy - int(r * 0.7)),
        ]
        for a, b in zip(pts, pts[1:]):
            cv2.line(img, a, b, int(ink), thickness, cv2.LINE_AA)
    elif style == "cross":
        d = int(r * 0.75)
        cv2.line(img, (icx - d, icy - d), (icx + d, icy + d), int(ink), thickness, cv2.LINE_AA)
        cv2.line(img, (icx - d, icy + d), (icx + d, icy - d), int(ink), thickness, cv2.LINE_AA)
    elif style == "scribble":
        y = icy - int(r * 0.6)
        step = max(2, int(r * 0.4))
        while y < icy + r * 0.6:
            x0 = icx - int(r * 0.7) + int(rng.integers(-2, 3))
            x1 = icx + int(r * 0.7) + int(rng.integers(-2, 3))
            shade = int(np.clip(ink + rng.integers(-20, 21), 0, 255))
            cv2.line(img, (x0, y), (x1, y), shade, max(1, step - 1), cv2.LINE_AA)
            y += step
    elif style == "edge":
        rad = max(1, int(round(r * coverage)))
        cv2.circle(img, (icx + int(r * 0.5), icy + int(r * 0.35)), rad, int(ink), -1)


# ---------------------------------------------------------------------------
# Capture damage
# ---------------------------------------------------------------------------

def cap_defocus(img: np.ndarray, sigma: float = 2.0) -> np.ndarray:
    """Out of focus lens. Softens fiducial edges and bubble rings alike."""
    k = int(sigma * 6) | 1
    return cv2.GaussianBlur(img, (k, k), sigma)


def cap_motion(img: np.ndarray, length: int = 15, angle_deg: float = 20.0) -> np.ndarray:
    """Hand shake. Directional smear, much harsher on thin printed rings."""
    length = max(3, length | 1)
    kernel = np.zeros((length, length), dtype=np.float32)
    kernel[length // 2, :] = 1.0
    M = cv2.getRotationMatrix2D((length / 2 - 0.5, length / 2 - 0.5), angle_deg, 1.0)
    kernel = cv2.warpAffine(kernel, M, (length, length))
    s = kernel.sum()
    if s > 0:
        kernel /= s
    return cv2.filter2D(img, -1, kernel)


def cap_low_light(img: np.ndarray, gain: float = 0.35, gamma: float = 1.6) -> np.ndarray:
    """
    Underexposure. Paper stops being near white, so any threshold calibrated on
    "paper is bright" quietly stops working.
    """
    x = img.astype(np.float32) / 255.0
    x = np.power(x, gamma) * gain
    return np.clip(x * 255.0, 0, 255).astype(np.uint8)


def cap_shadow(img: np.ndarray, strength: float = 0.55, angle_deg: float = 30.0) -> np.ndarray:
    """
    A hand or window casting a gradient across the page. This is the case a
    single global threshold cannot survive: one corner of the paper is darker
    than the ink in the opposite corner.
    """
    h, w = img.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    th = np.deg2rad(angle_deg)
    proj = (xx * np.cos(th) + yy * np.sin(th))
    proj = (proj - proj.min()) / max(float(np.ptp(proj)), 1e-6)
    ramp = 1.0 - strength * proj
    return np.clip(img.astype(np.float32) * ramp, 0, 255).astype(np.uint8)


def cap_vignette(img: np.ndarray, strength: float = 0.45) -> np.ndarray:
    """Lens falloff. Corners darken, which is exactly where the fiducials are."""
    h, w = img.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cy, cx = h / 2.0, w / 2.0
    d = np.sqrt(((xx - cx) / cx) ** 2 + ((yy - cy) / cy) ** 2)
    mask = 1.0 - strength * np.clip(d / np.sqrt(2.0), 0, 1) ** 2
    return np.clip(img.astype(np.float32) * mask, 0, 255).astype(np.uint8)


def cap_noise(img: np.ndarray, sigma: float = 8.0, rng=None) -> np.ndarray:
    """Sensor noise, which rises steeply in low light."""
    rng = rng or np.random.default_rng(0)
    n = rng.normal(0.0, sigma, img.shape)
    return np.clip(img.astype(np.float32) + n, 0, 255).astype(np.uint8)


def cap_jpeg(img: np.ndarray, quality: int = 45) -> np.ndarray:
    """Phone JPEG. Ringing around high contrast edges such as the QR and fiducials."""
    ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), int(quality)])
    if not ok:
        return img
    out = cv2.imdecode(buf, cv2.IMREAD_GRAYSCALE)
    return out if out is not None else img


def cap_on_surface(
    img: np.ndarray,
    *,
    surface: int = 90,
    margin_frac: float = 0.12,
    keystone: float = 0.0,
    rotate_deg: float = 0.0,
    rng=None,
) -> np.ndarray:
    """
    Place the page on a surface and photograph it at an angle.

    This is the single most important degradation, and the one the original
    pipeline had no answer for. Once the page does not fill the frame, a global
    threshold over the whole image separates PAPER from DESK, not INK from
    PAPER, and every fiducial dissolves into the page silhouette.

    surface
        Grey level of the desk. 235 is a white table, 90 a wooden one, 40 a
        dark mat. The failure is not gradual: it has a cliff.
    keystone
        0 is straight on. 0.25 is a steep handheld angle.
    """
    rng = rng or np.random.default_rng(0)
    h, w = img.shape[:2]
    mx, my = int(w * margin_frac), int(h * margin_frac)
    canvas = np.full((h + 2 * my, w + 2 * mx), int(surface), dtype=np.uint8)

    # Real desks are not flat grey; give the surface some texture so page
    # detection cannot cheat by looking for a perfectly uniform border.
    tex = rng.normal(0.0, 6.0, canvas.shape)
    canvas = np.clip(canvas.astype(np.float32) + tex, 0, 255).astype(np.uint8)

    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dst = np.float32([[mx, my], [mx + w, my], [mx + w, my + h], [mx, my + h]])
    if keystone:
        k = keystone
        dst = np.float32([
            [mx + w * k * 0.5, my + h * k * 0.25],
            [mx + w * (1 - k * 0.1), my],
            [mx + w * (1 - k * 0.4), my + h * (1 - k * 0.1)],
            [mx + w * k * 0.15, my + h],
        ])
    M = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(
        img, M, (canvas.shape[1], canvas.shape[0]),
        flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_TRANSPARENT, dst=canvas.copy(),
    )
    # A photographed page casts a slight shadow along one edge.
    out = warped
    if rotate_deg:
        cy, cx = out.shape[0] / 2.0, out.shape[1] / 2.0
        R = cv2.getRotationMatrix2D((cx, cy), rotate_deg, 1.0)
        out = cv2.warpAffine(
            out, R, (out.shape[1], out.shape[0]),
            flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE,
        )
    return out


def cap_rotate180(img: np.ndarray) -> np.ndarray:
    """Sheet fed upside down. Four identical corner squares cannot tell you."""
    return cv2.rotate(img, cv2.ROTATE_180)


def cap_resize(img: np.ndarray, scale: float) -> np.ndarray:
    interp = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC
    return cv2.resize(img, None, fx=scale, fy=scale, interpolation=interp)
