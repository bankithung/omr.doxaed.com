"""
results.views — Student results + review queue endpoints.

GET  /api/v1/results/?test=<id>    → StudentResult list (child-scoped)
GET  /api/v1/review/?test=<id>     → open ReviewItems (child-scoped)
POST /api/v1/review/<id>/resolve/  → resolve a ReviewItem (recompute result)
"""
from __future__ import annotations

from decimal import Decimal

from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from results.models import QuestionResponse, ReviewItem, StudentResult
from results.serializers import (
    ResolveReviewSerializer,
    ReviewItemSerializer,
    StudentResultSerializer,
)


class StudentResultListView(generics.ListAPIView):
    """
    GET /api/v1/results/?test=<id>

    Returns StudentResults scoped to request.user via test__user.
    Optional ?test= filter narrows to a specific test.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = StudentResultSerializer

    def get_queryset(self):
        qs = StudentResult.objects.filter(
            test__user=self.request.user
        ).prefetch_related("responses")
        test_id = self.request.query_params.get("test")
        if test_id:
            qs = qs.filter(test_id=test_id)
        return qs


class ReviewItemListView(generics.ListAPIView):
    """
    GET /api/v1/review/?test=<id>

    Returns open (resolved=False) ReviewItems scoped to request.user.
    Filters through omr_sheet__test__user or scan_job__batch__test__user.
    Optional ?test= filter narrows to a specific test.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ReviewItemSerializer

    def get_queryset(self):
        user = self.request.user
        test_id = self.request.query_params.get("test")

        # Filter open items scoped to this user via omr_sheet's test
        qs = ReviewItem.objects.filter(
            resolved=False,
            omr_sheet__test__user=user,
        )
        if test_id:
            qs = qs.filter(omr_sheet__test_id=test_id)
        return qs


class ResolveReviewItemView(APIView):
    """
    POST /api/v1/review/<id>/resolve/

    Body: {marked_options: [labels]}

    Corrects the QuestionResponse for the first flagged question on this
    ReviewItem's OmrSheet, recomputes the StudentResult score/counts/needs_review,
    and marks the ReviewItem resolved.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        # Scope check: must belong to request.user via omr_sheet__test__user
        review_item = get_object_or_404(
            ReviewItem,
            pk=pk,
            omr_sheet__test__user=request.user,
            resolved=False,
        )

        serializer = ResolveReviewSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        marked_options = serializer.validated_data["marked_options"]

        omr_sheet = review_item.omr_sheet
        if omr_sheet is None:
            return Response(
                {"detail": "ReviewItem has no associated OmrSheet."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Find the StudentResult for this sheet
        try:
            student_result = StudentResult.objects.get(omr_sheet=omr_sheet)
        except StudentResult.DoesNotExist:
            return Response(
                {"detail": "No StudentResult found for this sheet."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Find the first flagged QuestionResponse for this result
        flagged_response = QuestionResponse.objects.filter(
            student_result=student_result,
            flagged=True,
        ).first()

        if flagged_response is None:
            # Fall back: just mark the review item resolved with no response change
            review_item.resolved = True
            review_item.resolved_by = request.user
            review_item.resolution = {"marked_options": marked_options, "note": "no_flagged_response"}
            review_item.save(update_fields=["resolved", "resolved_by", "resolution"])
            return Response({"detail": "Resolved (no flagged response found)."})

        # Update the marked_options on the flagged response
        flagged_response.marked_options = marked_options

        # Recompute is_correct by comparing to the answer key
        answer_key = omr_sheet.answer_key  # {str(q_pos): [correct_labels]}
        correct_labels = set(answer_key.get(str(flagged_response.q_pos), []))
        marked_set = set(marked_options)
        flagged_response.is_correct = (marked_set == correct_labels and bool(correct_labels))
        flagged_response.flagged = False  # clear flag after resolution
        flagged_response.save(update_fields=["marked_options", "is_correct", "flagged"])

        # Recompute the StudentResult totals from all responses
        _recompute_student_result(student_result, omr_sheet)

        # Mark ReviewItem resolved
        review_item.resolved = True
        review_item.resolved_by = request.user
        review_item.resolution = {"marked_options": marked_options}
        review_item.save(update_fields=["resolved", "resolved_by", "resolution"])

        return Response(
            StudentResultSerializer(student_result).data,
            status=status.HTTP_200_OK,
        )


def _recompute_student_result(student_result, omr_sheet) -> None:
    """
    Recompute score/counts/needs_review on a StudentResult from its responses.
    Uses the answer_key + marking scheme from the OmrSheet's test.
    """
    from omr.scan.grade import grade_sheet

    # Build aggregated reads from current QuestionResponse objects
    aggregated_reads: dict[int, list] = {}
    for resp in student_result.responses.all():
        aggregated_reads[resp.q_pos] = list(resp.marked_options)

    grading = grade_sheet(omr_sheet, aggregated_reads)

    student_result.score = grading["score"]
    student_result.max_score = grading["max_score"]
    student_result.correct_count = grading["correct_count"]
    student_result.wrong_count = grading["wrong_count"]
    student_result.blank_count = grading["blank_count"]

    # Check if any responses are still flagged
    still_flagged = student_result.responses.filter(flagged=True).exists()
    # Check if any unresolved review items remain for this sheet
    open_reviews = ReviewItem.objects.filter(
        omr_sheet=omr_sheet,
        resolved=False,
    ).count()
    # Exclude the current one being resolved (it hasn't been saved yet at this point)
    # We will set needs_review based on still-flagged responses or remaining open review items
    student_result.needs_review = still_flagged or (open_reviews > 1)

    student_result.save(update_fields=[
        "score", "max_score", "correct_count", "wrong_count",
        "blank_count", "needs_review",
    ])
