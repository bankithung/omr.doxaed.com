"""
omr.codes — deterministic sheet-code generation.

Sheet code format: "{test_id:06d}-{token}"
where token = 8 URL-safe base32 chars derived from HMAC-SHA256(key=seed_bytes, msg=test_id_bytes).

The code is deterministic: same (test_id, seed) always produces the same result.
"""
import hashlib
import base64


def make_sheet_code(test_id: int, seed: int) -> tuple[str, str]:
    """
    Return (sheet_code, human_readable_code) deterministically from (test_id, seed).

    sheet_code          = "{test_id:06d}-{token}"  e.g. "000042-AB3DEFGH"
    human_readable_code = token  (the 8-char base32 suffix, easy to type)

    The token is 8 uppercase URL-safe base32 characters (A–Z, 2–7), making
    ~26^8 ≈ 2 × 10^11 possible values — sufficient for unique sheet codes at scale.
    """
    # Build a deterministic digest from (test_id, seed)
    raw = f"{test_id}:{seed}".encode()
    digest = hashlib.sha256(raw).digest()

    # Base32-encode and take the first 8 chars (5 bits each → 40 bits of entropy)
    # base64.b32encode uses A-Z and 2-7 (no padding issues with 8 chars from 32-byte digest)
    token = base64.b32encode(digest).decode("ascii")[:8]

    sheet_code = f"{test_id:06d}-{token}"
    human_readable_code = token
    return sheet_code, human_readable_code
