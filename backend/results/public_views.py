"""
results.public_views — NO-AUTH public portal endpoints.

All views resolve strictly by slug and serve only that one test's published data.
No auth context, no cross-tenant leakage.

Endpoints
---------
GET  /api/v1/public/r/<slug>/
    Portal meta: test_title, org_name, access_mode, show_leaderboard.
    404 if not published.

POST /api/v1/public/r/<slug>/lookup/
    Body: {roll_number, access_code?}
    Returns ONE matched student's result only.
    Throttled at "public_lookup" scope (30/min) to prevent brute-forcing.

GET  /api/v1/public/r/<slug>/leaderboard/
    Ranked list [{rank, name, score, percentile}] only when published + show_leaderboard.
"""
from __future__ import annotations

from django.contrib.auth.hashers import check_password
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from analytics.models import StudentProfile
from results.models import PublicResultShare, StudentResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_published_share(slug: str):
    """Return the PublicResultShare if it exists AND is_published; else return None."""
    try:
        share = PublicResultShare.objects.select_related("test__organization").get(slug=slug)
    except PublicResultShare.DoesNotExist:
        return None
    if not share.is_published:
        return None
    return share


def _mask_name(full_name: str) -> str:
    """Return a masked version: first letter + *** e.g. 'A***'."""
    if not full_name:
        return "***"
    return full_name[0] + "***"


def _student_name(share: PublicResultShare, student) -> str:
    """Return the display name respecting show_names."""
    if student is None:
        return "***"
    raw = student.full_name or ""
    if share.show_names:
        return raw
    return _mask_name(raw)


def _org_name(share: PublicResultShare) -> str | None:
    """Return the org name if the test belongs to an org, else None."""
    test = share.test
    org = getattr(test, "organization", None)
    if org is not None:
        return str(org)
    return None


# ---------------------------------------------------------------------------
# Portal meta
# ---------------------------------------------------------------------------

@api_view(["GET"])
@permission_classes([AllowAny])
def portal_meta(request, slug: str):
    """
    GET /api/v1/public/r/<slug>/

    Returns basic portal metadata.  404 if not published.
    No student data returned here.
    """
    share = _get_published_share(slug)
    if share is None:
        return Response({"detail": "Not found."}, status=404)

    return Response({
        "test_title": share.test.title,
        "org_name": _org_name(share),
        "access_mode": share.access_mode,
        "show_leaderboard": share.show_leaderboard,
    })


# ---------------------------------------------------------------------------
# Lookup throttle — custom class so the scope is set per-request
# ---------------------------------------------------------------------------

class PublicLookupThrottle(ScopedRateThrottle):
    scope = "public_lookup"


# ---------------------------------------------------------------------------
# Student lookup
# ---------------------------------------------------------------------------

@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([PublicLookupThrottle])
def portal_lookup(request, slug: str):
    """
    POST /api/v1/public/r/<slug>/lookup/

    Body: {roll_number, access_code?}

    Security properties
    -------------------
    - 404 if not published (same response as wrong slug — no oracle).
    - If access_mode='code': check via constant-time check_password; wrong/missing
      → 403 with generic message (does NOT reveal whether the roll exists).
    - Correct access or open mode: look up ONE matching result.
      Wrong roll → generic 404 "No result found".
    - NEVER returns more than the one matched result.
    - Names masked when show_names=False.
    - Throttled at public_lookup scope.
    """
    share = _get_published_share(slug)
    if share is None:
        return Response({"detail": "Not found."}, status=404)

    roll_number = request.data.get("roll_number", "")
    if not roll_number:
        return Response({"detail": "roll_number is required."}, status=400)

    # Access-code check BEFORE any roll lookup to prevent oracle attacks.
    if share.access_mode == PublicResultShare.ACCESS_CODE:
        provided_code = request.data.get("access_code", "") or ""
        # check_password is constant-time even when provided_code is empty.
        code_ok = bool(share.access_code_hash) and check_password(
            provided_code, share.access_code_hash
        )
        if not code_ok:
            return Response({"detail": "Invalid access code."}, status=403)

    # Find the single StudentResult for this test matching the roll number.
    # We go through StudentResult → student → roll_number, scoped STRICTLY to this test.
    result = (
        StudentResult.objects.select_related("student")
        .filter(test=share.test, student__roll_number=roll_number)
        .first()
    )
    if result is None:
        return Response({"detail": "No result found."}, status=404)

    student = result.student
    name = _student_name(share, student)
    roll = student.roll_number if student else roll_number

    # Enrich with percentile/rank from StudentProfile if available.
    percentile = None
    rank = None
    try:
        sp = StudentProfile.objects.get(test=share.test, result=result)
        percentile = sp.percentile
        rank = sp.rank
    except StudentProfile.DoesNotExist:
        pass

    return Response({
        "name": name,
        "roll_number": roll,
        "score": float(result.score),
        "max_score": float(result.max_score),
        "percentile": percentile,
        "rank": rank,
    })


# ---------------------------------------------------------------------------
# Leaderboard
# ---------------------------------------------------------------------------

@api_view(["GET"])
@permission_classes([AllowAny])
def portal_leaderboard(request, slug: str):
    """
    GET /api/v1/public/r/<slug>/leaderboard/

    Returns the ranked list only if published AND show_leaderboard.
    Respects show_names.
    """
    share = _get_published_share(slug)
    if share is None:
        return Response({"detail": "Not found."}, status=404)

    if not share.show_leaderboard:
        return Response({"detail": "Not found."}, status=404)

    # Fetch all StudentProfiles for this test, ordered by rank.
    profiles = (
        StudentProfile.objects.select_related("result__student")
        .filter(test=share.test)
        .order_by("rank", "id")
    )

    data = []
    for sp in profiles:
        student = sp.result.student if sp.result else None
        name = _student_name(share, student)
        data.append({
            "rank": sp.rank,
            "name": name,
            "score": sp.score,
            "percentile": sp.percentile,
        })

    return Response(data)
