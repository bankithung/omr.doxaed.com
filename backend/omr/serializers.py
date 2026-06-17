"""
omr.serializers — DRF serializers for OmrSheet and the generation request.
"""
from rest_framework import serializers

from .models import OmrSheet


class OmrSheetSerializer(serializers.ModelSerializer):
    """Read serializer for OmrSheet."""

    pdf_url = serializers.SerializerMethodField()

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


class GenerateSerializer(serializers.Serializer):
    """Validates the generation request body."""

    test = serializers.IntegerField()
    roster = serializers.IntegerField()
    shuffle_questions = serializers.BooleanField(default=False)
    shuffle_options = serializers.BooleanField(default=False)
