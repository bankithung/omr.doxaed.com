from django.conf import settings
from django.db import models


class ScanBatch(models.Model):
    """
    One upload batch — groups all ScanJobs created from a single upload call.
    Child-scoped via test; queryset must be filtered through test__user=request.user.
    """

    STATUS_QUEUED = "queued"
    STATUS_PROCESSING = "processing"
    STATUS_DONE = "done"
    STATUS_CHOICES = [
        (STATUS_QUEUED, "Queued"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_DONE, "Done"),
    ]

    test = models.ForeignKey(
        "assessments.Test",
        on_delete=models.CASCADE,
        related_name="scan_batches",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="scan_batches",
    )
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_QUEUED,
    )
    total = models.IntegerField(default=0)
    processed = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "id"]

    def __str__(self):
        return f"ScanBatch test={self.test_id} status={self.status} {self.processed}/{self.total}"


class ScanJob(models.Model):
    """
    One page (one image file) within a ScanBatch.
    """

    STATUS_QUEUED = "queued"
    STATUS_DONE = "done"
    STATUS_NEEDS_REVIEW = "needs_review"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_QUEUED, "Queued"),
        (STATUS_DONE, "Done"),
        (STATUS_NEEDS_REVIEW, "Needs Review"),
        (STATUS_FAILED, "Failed"),
    ]

    batch = models.ForeignKey(
        ScanBatch,
        on_delete=models.CASCADE,
        related_name="jobs",
    )
    omr_sheet = models.ForeignKey(
        "omr.OmrSheet",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="scan_jobs",
    )
    page_no = models.IntegerField(default=1)
    image_file = models.FileField(upload_to="scans/", null=True, blank=True)
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_QUEUED,
    )
    confidence = models.FloatField(null=True, blank=True)
    error_reason = models.TextField(blank=True, default="")
    reads = models.JSONField(
        default=dict,
        help_text=(
            "Stores this page's bubble reads: "
            "{q_pos: {marked: [labels], flag: str|null}, roll: str, flags: [str]}"
        ),
    )

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"ScanJob batch={self.batch_id} page={self.page_no} status={self.status}"


class GenerationEvent(models.Model):
    """
    One row per generation call — used to enforce the ≤5 generations/day free-tier gate.
    organization is set when the generation happens in an org scope (null = solo user).
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
    organization = models.ForeignKey(
        "organizations.Organization",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="generation_events",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"GenerationEvent user={self.user_id} test={self.test_id} at {self.created_at}"


class ScanEvent(models.Model):
    """
    One row per scan job processed — used to enforce the monthly scan limit per org.
    organization is set when the scan happens in an org scope (null = solo user).
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="scan_events",
    )
    test = models.ForeignKey(
        "assessments.Test",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="scan_events",
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="scan_events",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"ScanEvent user={self.user_id} org={self.organization_id} at {self.created_at}"


class OmrSheet(models.Model):
    """
    One OMR answer sheet — child-scoped via its Test (no direct user FK).

    The test's owner (user or organization) implicitly scopes this model.
    Queryset access is always filtered through test__user=request.user (or org equivalent).
    """

    ASSEMBLY_PARTIAL = "partial"
    ASSEMBLY_READY = "ready"
    ASSEMBLY_COMPLETE = "complete"
    ASSEMBLY_CHOICES = [
        (ASSEMBLY_PARTIAL, "Partial"),
        (ASSEMBLY_READY, "Ready"),
        (ASSEMBLY_COMPLETE, "Complete"),
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
