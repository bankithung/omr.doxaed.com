"""
analytics.views — read-only analytics endpoints, scoped by test__user.
"""

from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from assessments.models import Test
from results.models import StudentResult
from analytics.services import improvement, student_detail, test_summary


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def test_analytics(request, test_id: int):
    """
    GET /api/v1/analytics/test/{test_id}/

    Return the test-level analytics summary.
    Scoped: the test must belong to request.user (404 otherwise).
    """
    test = get_object_or_404(Test, id=test_id, user=request.user)
    summary = test_summary(test)
    return Response(summary)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def student_detail_view(request, test_id: int, student_id: int):
    """
    GET /api/v1/analytics/test/{test_id}/student/{student_id}/

    Return per-student analytics detail (score, per_question, topic_accuracy).
    Scoped: the test must belong to request.user, and a StudentResult for
    (test, student) must exist — 404 otherwise.
    """
    test = get_object_or_404(Test, id=test_id, user=request.user)
    result = get_object_or_404(StudentResult, test=test, student_id=student_id)
    return Response(student_detail(result))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def improvement_view(request, test_id: int):
    """
    GET /api/v1/analytics/test/{test_id}/improvement/

    Return retest-chain improvement analytics.
    Scoped: the test must belong to request.user (404 otherwise).
    """
    test = get_object_or_404(Test, id=test_id, user=request.user)
    return Response(improvement(test))
