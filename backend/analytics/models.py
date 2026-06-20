"""
analytics.models — persisted psychometric profiles.

TestProfile  (OneToOne Test)
    Stores the full analytical profile JSON + metadata.

StudentProfile (per student per test)
    Stores per-student percentile, rank, score — designed for longitudinal extension.

Both tables are owner-scoped through their parent Test (no direct user FK).
"""

from django.core.serializers.json import DjangoJSONEncoder
from django.db import models

from common.models import UUIDModel


class TestProfile(UUIDModel):
    """
    Persisted analytical profile for one Test.

    One-to-one with assessments.Test.  Populated by the
    analytics.tasks.recompute_test_profile Celery task.

    Fields
    ------
    test           : OneToOne FK to assessments.Test
    profile        : JSONField — full psychometric profile dict
                     (see analytics.psychometrics.compute_test_profile)
    cohort_size    : int — number of StudentResults at computation time
    status         : "ok" | "insufficient_sample" | "no_results"
    generated_at   : datetime — when the profile was last computed
    """

    STATUS_OK = "ok"
    STATUS_INSUFFICIENT = "insufficient_sample"
    STATUS_NO_RESULTS = "no_results"
    STATUS_CHOICES = [
        (STATUS_OK, "OK"),
        (STATUS_INSUFFICIENT, "Insufficient Sample"),
        (STATUS_NO_RESULTS, "No Results"),
    ]

    test = models.OneToOneField(
        "assessments.Test",
        on_delete=models.CASCADE,
        related_name="profile",
    )
    # DjangoJSONEncoder serialises UUID / Decimal / datetime that the psychometric
    # profile embeds (student_id, question_id, student_result_id, …) → str.
    profile = models.JSONField(default=dict, encoder=DjangoJSONEncoder)
    cohort_size = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=32,
        choices=STATUS_CHOICES,
        default=STATUS_NO_RESULTS,
    )
    generated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-generated_at"]

    def __str__(self):
        return f"TestProfile test={self.test_id} n={self.cohort_size} status={self.status}"


class StudentProfile(UUIDModel):
    """
    Per-student psychometric summary within one test.

    Designed to extend longitudinally (Phase 7) — currently scoped to
    (test, student).  Populated by the same recompute_test_profile task.

    Fields
    ------
    test        : FK to assessments.Test
    student     : FK to rosters.Student (nullable — sheet may not have a student)
    result      : FK to results.StudentResult
    score       : raw score at computation time
    percentile  : % of cohort scoring ≤ this student (0–100)
    rank        : dense rank (1 = highest)
    cohort_size : cohort size at computation time
    """

    test = models.ForeignKey(
        "assessments.Test",
        on_delete=models.CASCADE,
        related_name="student_profiles",
    )
    student = models.ForeignKey(
        "rosters.Student",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="student_profiles",
    )
    result = models.ForeignKey(
        "results.StudentResult",
        on_delete=models.CASCADE,
        related_name="profile",
    )
    score = models.FloatField(default=0.0)
    percentile = models.FloatField(default=0.0)
    rank = models.PositiveIntegerField(default=1)
    cohort_size = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["rank", "id"]
        unique_together = [("test", "result")]
        indexes = [
            models.Index(fields=["test", "student"], name="sprofile_test_student_idx"),
        ]

    def __str__(self):
        return (
            f"StudentProfile test={self.test_id} student={self.student_id} "
            f"rank={self.rank} pct={self.percentile:.1f}"
        )
