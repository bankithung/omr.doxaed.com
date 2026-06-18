"""
common.logo_validators — reusable validators for uploaded logo images (S6).

Applied to Test.logo and Organization.logo ImageFields.

Constraints:
- Max file size: 2 MB
- Max image dimensions: 2000 x 2000 px
- Allowed content-types: image/png, image/jpeg
- PIL.Image.MAX_IMAGE_PIXELS guard is set at import time (decompression-bomb
  defense: the logo is drawn into every generated sheet).
"""
from django.core.exceptions import ValidationError
from PIL import Image

# --- Decompression-bomb defense ---
# Cap the maximum number of pixels allowed when opening any image.
# Default Pillow limit is 178,956,970 px (~179 MP); we cap much lower for
# logos since they only need to be ~200 px wide.
MAX_IMAGE_PIXELS = 4_000_000  # 4 MP (e.g. 2000×2000)
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS

# --- Upload constraints ---
MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB
MAX_DIMENSION_PX = 2000
ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg"}
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg"}


def validate_logo_image(value):
    """
    Django field validator for logo ImageFields.

    Checks:
    1. File size ≤ 2 MB
    2. Content-type in allowlist (png / jpeg)
    3. File extension in allowlist
    4. Image dimensions ≤ 2000 × 2000 px (via Pillow, with MAX_IMAGE_PIXELS guard)

    Raises ValidationError on any violation.
    """
    import os

    # 1. File size
    if hasattr(value, "size") and value.size > MAX_FILE_SIZE_BYTES:
        raise ValidationError(
            f"Logo file size must not exceed 2 MB "
            f"(got {value.size / 1024 / 1024:.1f} MB)."
        )

    # 2. Content-type (if provided by the upload)
    content_type = getattr(value, "content_type", None)
    if content_type and content_type not in ALLOWED_CONTENT_TYPES:
        raise ValidationError(
            f"Logo must be a PNG or JPEG image (got '{content_type}')."
        )

    # 3. File extension
    name = getattr(value, "name", "") or ""
    ext = os.path.splitext(name)[1].lower()
    if ext and ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"Logo must be a .png or .jpg/.jpeg file (got '{ext}')."
        )

    # 4. Image dimensions — open with Pillow; MAX_IMAGE_PIXELS already set above
    try:
        # Seek to start if possible (InMemoryUploadedFile)
        if hasattr(value, "seek"):
            value.seek(0)
        img = Image.open(value)
        img.verify()  # catches truncated / corrupt files
        # After verify() the file handle is consumed; re-open for size check
        if hasattr(value, "seek"):
            value.seek(0)
        img = Image.open(value)
        w, h = img.size
    except Exception as exc:
        raise ValidationError(f"Logo file is not a valid image: {exc}") from exc
    finally:
        if hasattr(value, "seek"):
            value.seek(0)

    if w > MAX_DIMENSION_PX or h > MAX_DIMENSION_PX:
        raise ValidationError(
            f"Logo dimensions must not exceed {MAX_DIMENSION_PX}×{MAX_DIMENSION_PX} px "
            f"(got {w}×{h})."
        )
