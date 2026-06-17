"""
omr.simulate — Synthetic scan simulator for testing the CV pipeline.

This module renders a generated OMR sheet and "fills" chosen bubbles at the
descriptor's exact coordinates, producing a fake scanned image that the
pipeline can recover answers from.

Key coordinate fact:
    The generator draws a descriptor bubble at canonical px (cx, cy) by
    mapping to ReportLab points. When you render that PDF back to a pixmap
    with the correct scale matrix, the bubble appears at pixel (cx, cy).
    So the rendered canonical image and the descriptor share the SAME
    top-left px coordinate system — you can draw filled discs at descriptor
    (cx, cy) directly to "fill" a bubble.
"""

import io

import cv2
import fitz
import numpy as np

from omr.generator import render_sheet_pdf


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_canonical_image(descriptor: dict, sheet_meta: dict, page: int = 0) -> np.ndarray:
    """
    Render one page of an OMR sheet to a uint8 grayscale ndarray at canonical
    pixel size (page_px[0] × page_px[1], top-left origin, white background).

    Rendering strategy:
        We compute a fitz.Matrix from the page rect so that the output is
        exactly (W, H) pixels without a separate cv2.resize call. This
        preserves QR-code resolution enough for pyzbar to decode.

    Parameters
    ----------
    descriptor : dict
        Returned by omr.geometry.build_template().
    sheet_meta : dict
        Required keys: sheet_code, human_readable_code, institution,
        test_title, subject, student_name, roll_label, roll_digits.
    page : int
        0-based page index to render (default 0).

    Returns
    -------
    np.ndarray  uint8 grayscale (H, W), white background, black ink.
    """
    pdf_bytes = render_sheet_pdf(sheet_meta, descriptor)
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    W, H = descriptor["page_px"]
    fitz_page = doc[page]

    # Compute exact scale factors so the pixmap is exactly W×H pixels.
    # Using fitz.Matrix rather than dpi= avoids rounding to (W, H±1).
    scale_x = W / fitz_page.rect.width
    scale_y = H / fitz_page.rect.height
    mat = fitz.Matrix(scale_x, scale_y)

    pix = fitz_page.get_pixmap(matrix=mat)

    # Convert pixmap bytes → PIL → numpy RGB → grayscale
    img_bytes = pix.tobytes("png")
    from PIL import Image as PILImage
    img_pil = PILImage.open(io.BytesIO(img_bytes)).convert("L")  # 'L' = grayscale
    img = np.array(img_pil, dtype=np.uint8)

    # Safety resize if fitz still returns a different shape (edge case)
    if img.shape != (H, W):
        img = cv2.resize(img, (W, H), interpolation=cv2.INTER_AREA)

    return img


def simulate_scan(
    descriptor: dict,
    sheet_meta: dict,
    marked: dict,
    roll: str,
    page: int = 0,
    transform: np.ndarray | None = None,
) -> np.ndarray:
    """
    Produce a synthetic scanned image of an OMR sheet with chosen bubbles
    filled in.

    Parameters
    ----------
    descriptor : dict
        Returned by omr.geometry.build_template().
    sheet_meta : dict
        Required keys as for render_canonical_image().
    marked : dict
        {q_pos (int): [labels (str)]} — which option labels to fill per
        question position (0-indexed printed position).
        Example: {0: ["A"], 2: ["B", "C"]} fills option A on q0, B+C on q2.
    roll : str
        Roll number string, one digit per column.
        Length must be ≤ descriptor["roll_grid"]["cols"].
        E.g. "042" fills column-0→digit 0, column-1→digit 4, column-2→digit 2.
    page : int
        0-based page index (default 0).  Only answer bubbles assigned to this
        page are filled; roll grid is only drawn on page 0.
    transform : np.ndarray | None
        Optional 3×3 homography ndarray. When provided, the image is warped
        via cv2.warpPerspective so that the CV pipeline must un-warp it.
        Use perspective_transform() to build a mild corner-jitter homography.

    Returns
    -------
    np.ndarray  uint8 grayscale (H, W).
    """
    img = render_canonical_image(descriptor, sheet_meta, page)
    W, H = descriptor["page_px"]

    # ------------------------------------------------------------------
    # Fill answer bubbles
    # ------------------------------------------------------------------
    # Build a lookup: q_pos → {label → (cx, cy, r)} for bubbles on this page
    bubble_lookup: dict[int, dict[str, tuple[int, int, int]]] = {}
    for entry in descriptor["answer_bubbles"]:
        if entry["page"] != page:
            continue
        q_pos = entry["q_pos"]
        bubble_lookup[q_pos] = {
            opt["label"]: (int(opt["cx"]), int(opt["cy"]), int(opt["r"]))
            for opt in entry["options"]
        }

    for q_pos, labels in marked.items():
        if q_pos not in bubble_lookup:
            continue
        opts = bubble_lookup[q_pos]
        for label in labels:
            if label not in opts:
                continue
            cx, cy, r = opts[label]
            fill_r = max(1, int(r * 0.7))
            cv2.circle(img, (cx, cy), fill_r, 0, -1)  # 0 = black, -1 = filled

    # ------------------------------------------------------------------
    # Fill roll-number bubbles (page 0 only)
    # ------------------------------------------------------------------
    if page == 0 and roll:
        rg = descriptor["roll_grid"]
        ox, oy = int(rg["origin"][0]), int(rg["origin"][1])
        col_pitch = int(rg["col_pitch"])
        row_pitch = int(rg["row_pitch"])
        radius = int(rg["radius"])
        fill_r = max(1, int(radius * 0.7))

        for col_idx, digit_char in enumerate(roll):
            if col_idx >= rg["cols"]:
                break
            if not digit_char.isdigit():
                continue
            digit = int(digit_char)
            cx = ox + col_idx * col_pitch
            cy = oy + digit * row_pitch
            cv2.circle(img, (cx, cy), fill_r, 0, -1)

    # ------------------------------------------------------------------
    # Optional perspective warp
    # ------------------------------------------------------------------
    if transform is not None:
        img = cv2.warpPerspective(img, transform, (W, H), borderValue=255)

    return img


def perspective_transform(W: int, H: int, jitter_px: float = 15.0) -> np.ndarray:
    """
    Build a mild corner-jitter homography for robustness testing.

    Shifts each corner of the image inward/outward by up to jitter_px pixels
    in a fixed pattern (no randomness — deterministic for reproducible tests).

    Parameters
    ----------
    W, H : int
        Image width and height in pixels.
    jitter_px : float
        Maximum pixel shift at each corner (default 15).

    Returns
    -------
    np.ndarray  Shape (3, 3), float64 homography matrix.
    """
    j = jitter_px
    src = np.array([
        [0,   0  ],
        [W-1, 0  ],
        [0,   H-1],
        [W-1, H-1],
    ], dtype=np.float32)

    # Mild, fixed jitter pattern (deterministic)
    dst = np.array([
        [j,       j      ],
        [W-1-j/2, j/2    ],
        [j/2,     H-1-j  ],
        [W-1-j,   H-1-j/2],
    ], dtype=np.float32)

    H_mat = cv2.getPerspectiveTransform(src, dst)
    return H_mat
