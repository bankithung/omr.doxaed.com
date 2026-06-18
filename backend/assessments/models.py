from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from common.models import OwnerScopedModel
from common.logo_validators import validate_logo_image


class ClassGroup(OwnerScopedModel):
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    class Meta(OwnerScopedModel.Meta):
        ordering = ["name", "id"]

    def __str__(self):
        return self.name


class Test(OwnerScopedModel):
    DRAFT, READY, CLOSED = "draft", "ready", "closed"
    STATUS_CHOICES = [(DRAFT, "Draft"), (READY, "Ready"), (CLOSED, "Closed")]

    MODE_STANDARD = "standard"
    MODE_ROSTER_PREBUBBLED = "roster_prebubbled"
    MODE_COMPETITIVE = "competitive"
    MODE_CHOICES = [
        (MODE_STANDARD, "Standard"),
        (MODE_ROSTER_PREBUBBLED, "Roster (Pre-bubbled roll)"),
        (MODE_COMPETITIVE, "Competitive (Sections)"),
    ]

    class_group = models.ForeignKey(ClassGroup, on_delete=models.CASCADE, related_name="tests")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    title = models.CharField(max_length=255)
    subject = models.CharField(max_length=255, blank=True)
    parent_test = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="retests"
    )
    attempt_number = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=DRAFT)
    mode = models.CharField(max_length=32, choices=MODE_CHOICES, default=MODE_STANDARD)
    template_spec = models.JSONField(default=dict, blank=True)
    default_options = models.PositiveSmallIntegerField(default=4)

    # --- Phase 3b branding fields (additive, optional) ---
    LOGO_POSITION_LEFT = "left"
    LOGO_POSITION_CENTER = "center"
    LOGO_POSITION_RIGHT = "right"
    LOGO_POSITION_CHOICES = [
        (LOGO_POSITION_LEFT, "Left"),
        (LOGO_POSITION_CENTER, "Center"),
        (LOGO_POSITION_RIGHT, "Right"),
    ]

    sheet_heading = models.CharField(max_length=255, blank=True, default="")
    logo = models.ImageField(
        upload_to="branding/logos/", null=True, blank=True,
        validators=[validate_logo_image],
    )
    logo_position = models.CharField(
        max_length=8, choices=LOGO_POSITION_CHOICES, default=LOGO_POSITION_LEFT
    )
    brand_inherit_org = models.BooleanField(default=True)

    class Meta(OwnerScopedModel.Meta):
        ordering = ["-created_at", "id"]

    def __str__(self):
        return self.title


class MarkingScheme(models.Model):
    test = models.OneToOneField(Test, on_delete=models.CASCADE, related_name="marking_scheme")
    marks_per_correct = models.DecimalField(max_digits=6, decimal_places=2, default=1)
    negative_marks_per_wrong = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    partial_marking = models.BooleanField(default=False)
    multiple_correct_allowed = models.BooleanField(default=False)


class Section(models.Model):
    POLICY_ALL = "all"
    POLICY_CHOOSE_K = "choose_k"
    POLICY_CHOICES = [(POLICY_ALL, "All"), (POLICY_CHOOSE_K, "Choose K")]

    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name="sections")
    key = models.CharField(max_length=16)
    label = models.CharField(max_length=255)
    order_index = models.PositiveIntegerField(default=0)
    q_start = models.PositiveIntegerField()
    q_end = models.PositiveIntegerField()
    policy = models.CharField(max_length=16, choices=POLICY_CHOICES, default=POLICY_ALL)
    choose_k = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["order_index", "id"]
        constraints = [
            models.UniqueConstraint(fields=["test", "key"], name="uniq_section_test_key"),
        ]

    def __str__(self):
        return f"Section {self.key} ({self.label}) test={self.test_id}"

    def clean(self):
        errors = {}
        if self.q_start and self.q_end and self.q_start > self.q_end:
            errors["q_start"] = "q_start must be <= q_end."
        if self.policy == self.POLICY_CHOOSE_K:
            if self.choose_k is None:
                errors["choose_k"] = "choose_k is required when policy is choose_k."
            elif self.q_start and self.q_end:
                range_size = self.q_end - self.q_start + 1
                if not (1 <= self.choose_k <= range_size):
                    errors["choose_k"] = f"choose_k must be between 1 and {range_size}."
        if errors:
            raise ValidationError(errors)

    def sync_question_membership(self):
        """
        Bulk-set Question.section for questions whose order_index (0-based) maps
        to 1-based ordinals in [q_start, q_end].
        """
        # Question.order_index is 0-based; q_start/q_end are 1-based ordinals.
        # 1-based ordinal = order_index + 1, so order_index in [q_start-1, q_end-1].
        Question.objects.filter(
            test=self.test,
            order_index__gte=self.q_start - 1,
            order_index__lte=self.q_end - 1,
        ).update(section=self)


class SectionMarkingScheme(models.Model):
    NEG_FLAT = "flat"
    NEG_FRACTIONAL = "fractional"
    NEG_KIND_CHOICES = [(NEG_FLAT, "Flat"), (NEG_FRACTIONAL, "Fractional")]

    section = models.OneToOneField(Section, on_delete=models.CASCADE, related_name="marking_scheme")
    marks_per_correct = models.DecimalField(max_digits=8, decimal_places=4, default=1)
    negative_marks_per_wrong = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    negative_kind = models.CharField(max_length=12, choices=NEG_KIND_CHOICES, default=NEG_FLAT)
    partial_marking = models.BooleanField(default=False)
    multiple_correct_allowed = models.BooleanField(default=False)
    qualify_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"SectionMarkingScheme section={self.section_id}"


class Question(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name="questions")
    order_index = models.PositiveIntegerField(default=0)
    text = models.TextField()
    image = models.ImageField(upload_to="questions/", null=True, blank=True)
    topic = models.CharField(max_length=255, blank=True)
    difficulty = models.CharField(max_length=20, blank=True)
    section = models.ForeignKey(
        Section, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="questions"
    )

    class Meta:
        ordering = ["order_index", "id"]


class Option(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="options")
    label = models.CharField(max_length=4)
    text = models.CharField(max_length=500, blank=True)
    image = models.ImageField(upload_to="options/", null=True, blank=True)
    is_correct = models.BooleanField(default=False)

    class Meta:
        ordering = ["label", "id"]
