"""
analytics.views — read-only analytics endpoints, scoped by test__user.
"""

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from assessments.models import Test
from common.scope import scope_filter
from results.models import StudentResult
from analytics.services import improvement, student_detail, test_summary
from analytics.models import TestProfile, StudentProfile


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def test_analytics(request, test_id: int):
    """
    GET /api/v1/analytics/test/{test_id}/

    Return the test-level analytics summary.
    Scoped: the test must belong to the current scope (solo or org) — 404 otherwise.
    """
    test = get_object_or_404(Test.objects.filter(scope_filter(request)), id=test_id)
    summary = test_summary(test)
    return Response(summary)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def student_detail_view(request, test_id: int, student_id: int):
    """
    GET /api/v1/analytics/test/{test_id}/student/{student_id}/

    Return per-student analytics detail (score, per_question, topic_accuracy).
    Scoped: the test must belong to the current scope (solo or org), and a StudentResult for
    (test, student) must exist — 404 otherwise.
    """
    test = get_object_or_404(Test.objects.filter(scope_filter(request)), id=test_id)
    result = get_object_or_404(StudentResult, test=test, student_id=student_id)
    detail = student_detail(result)

    # Enrich with percentile + rank from StudentProfile (if available)
    try:
        sp = StudentProfile.objects.get(test=test, result=result)
        detail["percentile"] = sp.percentile
        detail["rank"] = sp.rank
        detail["cohort_size"] = sp.cohort_size
    except StudentProfile.DoesNotExist:
        detail["percentile"] = None
        detail["rank"] = None
        detail["cohort_size"] = None

    return Response(detail)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def improvement_view(request, test_id: int):
    """
    GET /api/v1/analytics/test/{test_id}/improvement/

    Return retest-chain improvement analytics.
    Scoped: the test must belong to the current scope (solo or org) — 404 otherwise.
    """
    test = get_object_or_404(Test.objects.filter(scope_filter(request)), id=test_id)
    return Response(improvement(test))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def test_profile_view(request, test_id: int):
    """
    GET /api/v1/analytics/test/{test_id}/profile/

    Return (or compute on the fly) the psychometric TestProfile for a test.
    If the profile has not been computed yet, triggers computation synchronously
    before responding.

    Scoped: the test must belong to the current scope (solo or org) — 404 otherwise.
    """
    test = get_object_or_404(Test.objects.filter(scope_filter(request)), id=test_id)

    # Try to fetch a pre-computed profile
    try:
        tp = TestProfile.objects.get(test=test)
    except TestProfile.DoesNotExist:
        tp = None

    if tp is None:
        # Compute on the fly (synchronous — always_eager in dev; fast in any env)
        from analytics.tasks import recompute_test_profile
        recompute_test_profile(test_id)
        try:
            tp = TestProfile.objects.get(test=test)
        except TestProfile.DoesNotExist:
            # Still nothing (no results yet)
            return Response(
                {"detail": "No results available for this test."},
                status=404,
            )

    return Response({
        "test_id": test_id,
        "cohort_size": tp.cohort_size,
        "status": tp.status,
        "generated_at": tp.generated_at.isoformat() if tp.generated_at else None,
        "profile": tp.profile,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def student_report_card_view(request, test_id: int, student_id: int):
    """
    GET /api/v1/analytics/test/{test_id}/student/{student_id}/report-card/

    Return a two-page A4 PDF report card for a single student.
    Scoped: the test must belong to the current scope — 404 otherwise.
    A StudentResult for (test, student) must exist — 404 otherwise.
    """
    from analytics.report_card import student_report_card

    test = get_object_or_404(
        Test.objects.select_related("organization", "user").filter(scope_filter(request)),
        id=test_id,
    )
    result = get_object_or_404(
        StudentResult.objects.select_related("student", "omr_sheet")
        .prefetch_related("responses__question"),
        test=test,
        student_id=student_id,
    )

    pdf_bytes = student_report_card(test, result)

    student = result.student
    name = (student.full_name or "student") if student else "student"
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
    safe_title = "".join(c if c.isalnum() or c in "-_" else "_" for c in test.title)
    filename = f"report_card_{safe_title}_{safe_name}.pdf"

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def bulk_report_cards_view(request, test_id: int):
    """
    GET /api/v1/analytics/test/{test_id}/report-cards/

    Return one combined PDF of all graded students for the test (2 pages each).
    Scoped: the test must belong to the current scope — 404 otherwise.
    """
    from analytics.report_card import bulk_report_cards

    test = get_object_or_404(
        Test.objects.select_related("organization", "user").filter(scope_filter(request)),
        id=test_id,
    )

    pdf_bytes = bulk_report_cards(test)

    safe_title = "".join(c if c.isalnum() or c in "-_" else "_" for c in test.title)
    filename = f"report_cards_{safe_title}.pdf"

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def export_view(request, test_id: int):
    """
    GET /api/v1/analytics/test/{test_id}/export/?output_format=csv|xlsx|pdf

    Return the test results as a downloadable file.
    Scoped: the test must belong to the current scope (solo or org) — 404 otherwise.
    Unknown format → 400.

    Note: the query parameter is named ``output_format`` (not ``format``) to
    avoid conflicting with DRF's built-in ``?format=`` content-negotiation
    parameter, which would intercept ``?format=csv`` and return 404/406
    before the view body runs.

    Supported formats
    -----------------
    csv  → text/csv
    xlsx → application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
    pdf  → application/pdf
    """
    from analytics.export import results_csv, results_xlsx, report_pdf

    test = get_object_or_404(Test.objects.filter(scope_filter(request)), id=test_id)

    fmt = request.query_params.get("output_format", "csv").lower()

    safe_title = "".join(c if c.isalnum() or c in "-_" else "_" for c in test.title)

    if fmt == "csv":
        data = results_csv(test)
        content_type = "text/csv"
        filename = f"results_{safe_title}.csv"
    elif fmt == "xlsx":
        data = results_xlsx(test)
        content_type = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        filename = f"results_{safe_title}.xlsx"
    elif fmt == "pdf":
        data = report_pdf(test)
        content_type = "application/pdf"
        filename = f"report_{safe_title}.pdf"
    else:
        return Response(
            {"detail": f"Unknown format {fmt!r}. Use csv, xlsx, or pdf."},
            status=400,
        )

    response = HttpResponse(data, content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
