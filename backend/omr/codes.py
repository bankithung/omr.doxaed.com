"""
omr.codes — deterministic sheet-code generation.

Sheet code format: "{test_id:06d}-{token}"
where token = 8 URL-safe base32 chars derived from HMAC-SHA256(key=seed_bytes, msg=test_id_bytes).

The code is deterministic: same (test_id, seed) always produces the same result.
"""
import hashlib
import base64


def make_sheet_code(test_id, seed: int) -> tuple[str, str]:
    """
    Return (sheet_code, human_readable_code) deterministically from (test_id, seed).

    sheet_code          = "{test_hex}-{token}"  e.g. "8f3a9c1e4b2d...-AB3DEFGH"
    human_readable_code = token  (the 8-char base32 suffix, easy to type)

    test_hex = the test's UUID as 32 hex chars (recoverable, so the scan side can
    validate a sheet belongs to the right test); the token guarantees uniqueness
    per (test, seed). The token is 8 uppercase base32 chars (A–Z, 2–7).
    """
    # Build a deterministic digest from (test_id, seed)
    raw = f"{test_id}:{seed}".encode()
    digest = hashlib.sha256(raw).digest()

    # Base32-encode and take the first 8 chars (5 bits each → 40 bits of entropy)
    # base64.b32encode uses A-Z and 2-7 (no padding issues with 8 chars from 32-byte digest)
    token = base64.b32encode(digest).decode("ascii")[:8]

    # Short test prefix (first 8 hex of the UUID) for human grouping — keeps the
    # sheet code (and therefore the printed QR payload) SHORT so it decodes
    # reliably from real scans. Uniqueness/security comes from the HMAC token,
    # and the scan side resolves the sheet by full code + batch test anyway.
    prefix = str(test_id).replace("-", "")[:8]
    sheet_code = f"{prefix}-{token}"
    human_readable_code = token
    return sheet_code, human_readable_code
