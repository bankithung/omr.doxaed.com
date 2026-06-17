"""
analytics.views — read-only analytics endpoints, scoped by test__user.
"""

from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from assessments.models import Test
from analytics.services import test_summary


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
