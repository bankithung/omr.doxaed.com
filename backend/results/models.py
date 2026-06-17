from django.conf import settings
from django.db import models


class StudentResult(models.Model):
    """
    Graded result for one student on one test.
    Child-scoped via test; queryset must be filtered through test__user=request.user.
    """

    test = models.ForeignKey(
        "assessments.Test",
        on_delete=models.CASCADE,
        related_name="student_results",
    )
    student = models.ForeignKey(
        "rosters.Student",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="student_results",
    )
    omr_sheet = models.ForeignKey(
        "omr.OmrSheet",
        on_delete=models.CASCADE,
        related_name="student_results",
    )
    score = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    max_score = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    correct_count = models.IntegerField(default=0)
    wrong_count = models.IntegerField(default=0)
    blank_count = models.IntegerField(default=0)
    needs_review = models.BooleanField(default=False)
    graded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-graded_at", "id"]
        indexes = [
            models.Index(fields=["test", "student"], name="studentresult_test_student_idx"),
            models.Index(fields=["graded_at"], name="studentresult_graded_at_idx"),
        ]

    def __str__(self):
        return f"StudentResult test={self.test_id} student={self.student_id} score={self.score}"


class QuestionResponse(models.Model):
    """
    Per-question read + grading outcome within a StudentResult.
    """

    student_result = models.ForeignKey(
        StudentResult,
        on_delete=models.CASCADE,
        related_name="responses",
    )
    question = models.ForeignKey(
        "assessments.Question",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="question_responses",
    )
    q_pos = models.IntegerField()
    marked_options = models.JSONField(default=list)
    is_correct = models.BooleanField(default=False)
    flagged = models.BooleanField(default=False)

    class Meta:
        ordering = ["q_pos", "id"]
        indexes = [
            models.Index(fields=["student_result", "question"], name="qresponse_result_question_idx"),
        ]

    def __str__(self):
        return f"QuestionResponse result={self.student_result_id} q_pos={self.q_pos}"


class ReviewItem(models.Model):
    """
    Manual review queue entry — one per flag raised during scanning/grading.
    """

    REASON_NO_QR = "no_qr"
    REASON_ALIGNMENT = "alignment"
    REASON_ROLL_UNREADABLE = "roll_unreadable"
    REASON_DOUBLE_MARK = "double_mark"
    REASON_FAINT = "faint"
    REASON_MISSING_PAGE = "missing_page"
    REASON_CHOICES = [
        (REASON_NO_QR, "No QR Code"),
        (REASON_ALIGNMENT, "Alignment Failed"),
        (REASON_ROLL_UNREADABLE, "Roll Unreadable"),
        (REASON_DOUBLE_MARK, "Double Mark"),
        (REASON_FAINT, "Faint / Ambiguous"),
        (REASON_MISSING_PAGE, "Missing Page"),
    ]

    scan_job = models.ForeignKey(
        "omr.ScanJob",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="review_items",
    )
    omr_sheet = models.ForeignKey(
        "omr.OmrSheet",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="review_items",
    )
    question = models.ForeignKey(
        "assessments.Question",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="review_items",
    )
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    resolved = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="resolved_review_items",
    )
    resolution = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "id"]

    def __str__(self):
        return f"ReviewItem reason={self.reason} resolved={self.resolved}"
