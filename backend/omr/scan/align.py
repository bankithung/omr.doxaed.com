"""
omr.scan.align — Scan alignment pipeline.

Three stages:
    1. decode_qr       — extract (sheet_code, page, total) from the QR code
    2. detect_fiducials — locate the 4 corner fiducial squares in image coords
    3. warp_to_canonical — perspective-warp the scan to the canonical 827×1169 space

All functions operate on uint8 grayscale numpy arrays.

QR resolution note
------------------
pyzbar struggles at 827×1169 for some payloads.  Real scans are higher DPI.
Callers should pass images rendered with simulate_scan(scale=2.0) →
1654×2338 px; the pipeline decodes the QR and locates fiducials at that
higher resolution, then warps DOWN to the canonical 827×1169 descriptor space.
"""

from __future__ import annotations

import cv2
import numpy as np
from pyzbar.pyzbar import decode as pyzbar_decode
from PIL import Image as PILImage


# ---------------------------------------------------------------------------
# Stage 1 — QR decode
# ---------------------------------------------------------------------------

def decode_qr(image: np.ndarray) -> tuple[str, int, int] | None:
    """
    Decode the first QR code found in *image* (uint8 grayscale or BGR).

    The expected QR payload format is ``"sheet_code|page|total"`` where
    *page* and *total* are 1-based integers.

    Parameters
    ----------
    image : np.ndarray
        uint8 grayscale (H, W) or BGR (H, W, 3) image.

    Returns
    -------
    (sheet_code, page_number, total_pages) on success (page_number is 1-based
    as encoded in the QR), or ``None`` if no QR is present / unparseable.
    """
    # pyzbar works best on PIL images; convert from numpy
    if image.ndim == 2:
        pil_img = PILImage.fromarray(image, mode="L")
    else:
        # BGR → RGB for PIL
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_img = PILImage.fromarray(rgb)

    codes = pyzbar_decode(pil_img)
    for code in codes:
        if code.type != "QRCODE":
            continue
        try:
            payload = code.data.decode("utf-8")
            parts = payload.split("|")
            if len(parts) != 3:
                continue
            sheet_code = parts[0]
            page = int(parts[1])
            total = int(parts[2])
            return sheet_code, page, total
        except (ValueError, UnicodeDecodeError):
            continue
    return None


# ---------------------------------------------------------------------------
# Stage 2 — Fiducial detection
# ---------------------------------------------------------------------------

def detect_fiducials(
    image: np.ndarray,
    descriptor: dict,
) -> np.ndarray | None:
    """
    Detect the 4 corner fiducial squares in *image* and return their centroids.

    Algorithm
    ---------
    1. Convert to grayscale → Otsu inverse threshold (fiducials appear as
       white blobs on black background).
    2. findContours — external contours only.
    3. Filter candidates:
       - roughly square bounding box (aspect ratio within ±0.4 of 1.0)
       - solid (contour area / bounding-box area > 0.70)
       - plausible area: the canonical fiducial is FID×FID = 24×24 = 576 px²
         at 100 DPI.  In the scaled image that is (FID*scale)² px².  We accept
         blobs whose area falls within [0.25×expected, 4.0×expected] to be
         robust to rendering variation and moderate perspective distortion.
    4. For each of the 4 image corners (TL, TR, BL, BR), pick the qualifying
       blob whose centroid is nearest that corner.
    5. Compute centroid via cv2 moments.
    6. Return (4, 2) float32 array ordered TL, TR, BL, BR, or None if any
       corner is unmatched.

    Parameters
    ----------
    image : np.ndarray
        uint8 grayscale image (H, W).
    descriptor : dict
        Canonical descriptor from omr.geometry.build_template().  Used to
        derive the expected fiducial size (FID px in canonical space).

    Returns
    -------
    np.ndarray shape (4, 2) float32 of (x, y) centroids ordered TL, TR, BL,
    BR in image pixel coordinates, or ``None``.
    """
    if image.ndim != 2:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    H, W = gray.shape

    # Otsu threshold — inverse (fiducials = black ink → they become white after inversion)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Find external contours
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Estimate the expected fiducial size in image pixels.
    # Canonical FID = 24 px; the image may be scaled relative to canonical (W, H).
    from omr.geometry import FID, W as CANON_W, H as CANON_H
    img_scale = W / CANON_W  # actual scale of this image vs canonical
    expected_area = (FID * img_scale) ** 2
    area_lo = expected_area * 0.20
    area_hi = expected_area * 6.0

    candidates = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < area_lo or area > area_hi:
            continue

        x, y, bw, bh = cv2.boundingRect(cnt)
        if bw == 0 or bh == 0:
            continue

        # Squareness check
        aspect = bw / bh
        if abs(aspect - 1.0) > 0.5:
            continue

        # Solidity check (filled square vs hollow shape)
        bbox_area = bw * bh
        solidity = area / bbox_area
        if solidity < 0.60:
            continue

        # Centroid via moments
        M = cv2.moments(cnt)
        if M["m00"] == 0:
            continue
        cx = M["m10"] / M["m00"]
        cy = M["m01"] / M["m00"]
        candidates.append((cx, cy))

    if len(candidates) < 4:
        return None

    # For each corner, pick the nearest candidate centroid.
    # Corners: TL=(0,0), TR=(W-1,0), BL=(0,H-1), BR=(W-1,H-1)
    corners = [
        (0.0,     0.0   ),  # TL
        (W - 1.0, 0.0   ),  # TR
        (0.0,     H - 1.0), # BL
        (W - 1.0, H - 1.0), # BR
    ]

    pts = np.array(candidates, dtype=np.float32)
    result = np.zeros((4, 2), dtype=np.float32)

    for i, (cx_corner, cy_corner) in enumerate(corners):
        dists = np.hypot(pts[:, 0] - cx_corner, pts[:, 1] - cy_corner)
        nearest = int(np.argmin(dists))
        result[i] = pts[nearest]

    # Sanity-check: each corner should have a *different* candidate
    if len(set(map(tuple, result.tolist()))) < 4:
        # Two corners mapped to the same blob — detection failed
        return None

    return result


# ---------------------------------------------------------------------------
# Stage 3 — Perspective warp to canonical space
# ---------------------------------------------------------------------------

def warp_to_canonical(
    image: np.ndarray,
    src_pts: np.ndarray,
    descriptor: dict,
) -> np.ndarray:
    """
    Perspective-warp *image* so that the 4 fiducial centres in *src_pts*
    align with their canonical positions defined in *descriptor*.

    The output is a grayscale image of exactly (H_canon, W_canon) pixels
    matching the descriptor's ``page_px`` dimensions (827×1169 for A4 at
    100 DPI).

    Parameters
    ----------
    image : np.ndarray
        uint8 grayscale input scan (any size).
    src_pts : np.ndarray
        Shape (4, 2) float32 — fiducial centroids in *image* pixel coords,
        ordered TL, TR, BL, BR (as returned by detect_fiducials).
    descriptor : dict
        Canonical descriptor from omr.geometry.build_template().

    Returns
    -------
    np.ndarray  uint8 grayscale (H_canon, W_canon) — perspective-corrected
    image in the canonical 100-DPI top-left-origin coordinate system.
    """
    if image.ndim != 2:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    W_canon, H_canon = descriptor["page_px"]

    # Destination points = canonical fiducial centres, ordered TL, TR, BL, BR
    fids = descriptor["fiducials"]
    dst_pts = np.array(
        [[f["cx"], f["cy"]] for f in fids],
        dtype=np.float32,
    )

    M = cv2.getPerspectiveTransform(src_pts.astype(np.float32), dst_pts)
    warped = cv2.warpPerspective(
        gray,
        M,
        (W_canon, H_canon),
        flags=cv2.INTER_LINEAR,
        borderValue=255,
    )
    return warped
