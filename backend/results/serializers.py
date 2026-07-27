"""
results.serializers — DRF serializers for StudentResult, QuestionResponse, ReviewItem.
"""
from rest_framework import serializers

from results.models import QuestionResponse, ReviewItem, StudentResult


class QuestionResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionResponse
        fields = ("id", "q_pos", "marked_options", "is_correct", "flagged")
        read_only_fields = fields


class StudentResultSerializer(serializers.ModelSerializer):
    responses = QuestionResponseSerializer(many=True, read_only=True)
    student_roll = serializers.SerializerMethodField()
    student_name = serializers.SerializerMethodField()

    class Meta:
        model = StudentResult
        fields = (
            "id",
            "omr_sheet",
            "student",
            "student_roll",
            "student_name",
            "score",
            "max_score",
            "correct_count",
            "wrong_count",
            "blank_count",
            "disqualified_count",
            "needs_review",
            "graded_at",
            "responses",
        )
        read_only_fields = fields

    def get_student_roll(self, obj):
        if obj.student:
            return obj.student.roll_number
        return None

    def get_student_name(self, obj):
        if obj.student:
            return obj.student.full_name
        return None


class ReviewItemSerializer(serializers.ModelSerializer):
    sheet_code = serializers.SerializerMethodField()
    q_pos = serializers.SerializerMethodField()

    class Meta:
        model = ReviewItem
        fields = (
            "id",
            "scan_job",
            "omr_sheet",
            "sheet_code",
            "question",
            "q_pos",
            "reason",
            "resolved",
            "resolved_by",
            "resolution",
            "created_at",
        )
        read_only_fields = fields

    def get_sheet_code(self, obj):
        if obj.omr_sheet:
            return obj.omr_sheet.sheet_code
        return None

    def get_q_pos(self, obj):
        # The question this flag was raised for, recorded at scan time.
        #
        # This used to infer q_pos by taking the first flagged response on the
        # sheet, so every faint/double_mark card on a sheet reported the same
        # question no matter which one it was actually about. NULL here means
        # the reason is sheet-level and there is no single answer to correct.
        return obj.q_pos


class ResolveReviewSerializer(serializers.Serializer):
    """Payload for POST /api/v1/review/{id}/resolve/"""
    marked_options = serializers.ListField(
        child=serializers.CharField(max_length=8),
        allow_empty=True,
    )
