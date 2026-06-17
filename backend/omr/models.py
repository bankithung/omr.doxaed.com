from django.conf import settings
from django.db import models


class GenerationEvent(models.Model):
    """
    One row per generation call — used to enforce the ≤5 generations/day free-tier gate.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="generation_events",
    )
    test = models.ForeignKey(
        "assessments.Test",
        on_delete=models.CASCADE,
        related_name="generation_events",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"GenerationEvent user={self.user_id} test={self.test_id} at {self.created_at}"


class OmrSheet(models.Model):
    """
    One OMR answer sheet — child-scoped via its Test (no direct user FK).

    The test's owner (user or organization) implicitly scopes this model.
    Queryset access is always filtered through test__user=request.user (or org equivalent).
    """

    ASSEMBLY_PARTIAL = "partial"
    ASSEMBLY_READY = "ready"
    ASSEMBLY_CHOICES = [
        (ASSEMBLY_PARTIAL, "Partial"),
        (ASSEMBLY_READY, "Ready"),
    ]

    # Parent scoping
    test = models.ForeignKey(
        "assessments.Test",
        on_delete=models.CASCADE,
        related_name="omr_sheets",
    )
    student = models.ForeignKey(
        "rosters.Student",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="omr_sheets",
    )

    # Identity
    sheet_code = models.CharField(max_length=64, unique=True)
    human_readable_code = models.CharField(max_length=32)

    # Shuffle state (the seed used for deterministic generation)
    shuffle_version = models.BigIntegerField(default=0)

    # Per-sheet plan (from omr.shuffle.build_sheet_plan)
    question_order = models.JSONField(default=list)
    option_order = models.JSONField(default=dict)
    answer_key = models.JSONField(default=dict)

    # Geometry (from omr.geometry.build_template) — stored for Phase-4 scanner
    template_descriptor = models.JSONField(default=dict)
    page_count = models.IntegerField(default=1)
    page_map = models.JSONField(default=dict)

    # Generated PDF
    pdf_file = models.FileField(upload_to="omr_sheets/", null=True, blank=True)

    # Status
    assembly_status = models.CharField(
        max_length=16,
        choices=ASSEMBLY_CHOICES,
        default=ASSEMBLY_PARTIAL,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "id"]

    def __str__(self):
        return self.sheet_code
