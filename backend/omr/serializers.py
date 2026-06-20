"""
omr.serializers — DRF serializers for OmrSheet, generation request, scan batch.
"""
from rest_framework import serializers

from .models import OmrSheet, ScanBatch


class OmrSheetSerializer(serializers.ModelSerializer):
    """Read serializer for OmrSheet."""

    pdf_url = serializers.SerializerMethodField()
    question_paper_url = serializers.SerializerMethodField()

    class Meta:
        model = OmrSheet
        fields = (
            "id",
            "sheet_code",
            "human_readable_code",
            "student",
            "page_count",
            "assembly_status",
            "pdf_url",
            "question_paper_url",
            "question_order",
            "answer_key",
            "template_descriptor",
        )
        read_only_fields = fields

    def get_pdf_url(self, obj):
        if not obj.pdf_file:
            return None
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.pdf_file.url)
        return obj.pdf_file.url

    def get_question_paper_url(self, obj):
        """
        Return the AUTHENTICATED endpoint URL for the question paper.
        Never exposes the raw /media/ path — callers must fetch via this
        authenticated endpoint which enforces scope.
        Returns None when no question paper has been generated yet.
        """
        if not obj.question_paper_file:
            return None
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(
                f"/api/v1/omr/sheets/{obj.pk}/question-paper/"
            )
        return f"/api/v1/omr/sheets/{obj.pk}/question-paper/"


class GenerateSerializer(serializers.Serializer):
    """Validates the generation request body."""

    test = serializers.UUIDField()
    roster = serializers.UUIDField()
    # Optional subset of student ids to generate for. Empty/absent → whole roster.
    student_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, default=list
    )
    shuffle_questions = serializers.BooleanField(default=False)
    shuffle_options = serializers.BooleanField(default=False)
    emit_question_paper = serializers.BooleanField(default=False)

    def validate(self, attrs):
        # S7 / Phase 3a: force emit_question_paper when shuffle is on
        if attrs.get("shuffle_questions") or attrs.get("shuffle_options"):
            attrs["emit_question_paper"] = True
        return attrs


class ScanBatchSerializer(serializers.ModelSerializer):
    """Read serializer for ScanBatch progress."""

    class Meta:
        model = ScanBatch
        fields = ("id", "status", "total", "processed", "created_at")
        read_only_fields = fields
