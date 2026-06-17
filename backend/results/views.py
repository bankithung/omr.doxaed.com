"""
results.views — Student results + review queue endpoints.

GET  /api/v1/results/?test=<id>    → StudentResult list (child-scoped)
GET  /api/v1/review/?test=<id>     → open ReviewItems (child-scoped)
POST /api/v1/review/<id>/resolve/  → resolve a ReviewItem (recompute result)
"""
from __future__ import annotations

from decimal import Decimal

from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.scope import scope_filter
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
            scope_filter(self.request, "test__")
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
        test_id = self.request.query_params.get("test")

        # Filter open items scoped to the current scope (solo or org). Include both:
        #   - items tied to an OmrSheet (most flags), via omr_sheet__test__
        #   - orphaned items with no OmrSheet (e.g. no_qr), via scan_job__batch__test__
        sf_omr = scope_filter(self.request, "omr_sheet__test__")
        sf_scan = scope_filter(self.request, "scan_job__batch__test__")
        qs = ReviewItem.objects.filter(
            sf_omr | sf_scan,
            resolved=False,
        ).distinct()
        if test_id:
            qs = qs.filter(
                Q(omr_sheet__test_id=test_id) | Q(scan_job__batch__test_id=test_id)
            )
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
        # Scope check: must belong to the current scope (solo or org) via either
        # the omr_sheet's test OR (for orphaned items like no_qr) the scan_job's batch's test.
        sf_omr = scope_filter(request, "omr_sheet__test__")
        sf_scan = scope_filter(request, "scan_job__batch__test__")
        review_item = get_object_or_404(
            ReviewItem.objects.filter(sf_omr | sf_scan),
            pk=pk,
            resolved=False,
        )

        serializer = ResolveReviewSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        marked_options = serializer.validated_data["marked_options"]

        omr_sheet = review_item.omr_sheet

        # Find the StudentResult for this sheet (may not exist for no_qr items).
        student_result = None
        if omr_sheet is not None:
            student_result = StudentResult.objects.filter(omr_sheet=omr_sheet).first()

        # If we have a StudentResult, update the first flagged response (if any).
        if student_result is not None:
            flagged_response = QuestionResponse.objects.filter(
                student_result=student_result,
                flagged=True,
            ).first()

            if flagged_response is not None:
                # Update the marked_options on the flagged response.
                flagged_response.marked_options = marked_options
                # Recompute is_correct by comparing to the answer key.
                answer_key = omr_sheet.answer_key  # {str(q_pos): [correct_labels]}
                correct_labels = set(answer_key.get(str(flagged_response.q_pos), []))
                marked_set = set(marked_options)
                flagged_response.is_correct = (
                    marked_set == correct_labels and bool(correct_labels)
                )
                flagged_response.flagged = False  # clear flag after resolution
                flagged_response.save(
                    update_fields=["marked_options", "is_correct", "flagged"]
                )

        # Mark the ReviewItem resolved FIRST and SAVE it, so the recompute below
        # sees the up-to-date open-item state.
        review_item.resolved = True
        review_item.resolved_by = request.user
        review_item.resolution = {"marked_options": marked_options}
        review_item.save(update_fields=["resolved", "resolved_by", "resolution"])

        # ALWAYS recompute the StudentResult (clears needs_review when nothing is
        # still open/flagged) — in both the flagged-response and fallback paths.
        if student_result is not None:
            _recompute_student_result(student_result, omr_sheet)
            return Response(
                StudentResultSerializer(student_result).data,
                status=status.HTTP_200_OK,
            )

        # No StudentResult (e.g. an orphaned no_qr item) — just acknowledge.
        return Response(
            {"detail": "Resolved.", "id": review_item.id},
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

    # needs_review reflects what is ACTUALLY still open/flagged. The ReviewItem
    # being resolved is already saved as resolved=True before this runs, so it
    # is correctly excluded from the still_open check.
    still_open = ReviewItem.objects.filter(
        omr_sheet=omr_sheet,
        resolved=False,
    ).exists()
    still_flagged = student_result.responses.filter(flagged=True).exists()
    student_result.needs_review = still_open or still_flagged

    student_result.save(update_fields=[
        "score", "max_score", "correct_count", "wrong_count",
        "blank_count", "needs_review",
    ])
