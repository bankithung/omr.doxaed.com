from django.conf import settings
from django.db import models

from common.models import OwnerScopedModel


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

    class_group = models.ForeignKey(ClassGroup, on_delete=models.CASCADE, related_name="tests")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    title = models.CharField(max_length=255)
    subject = models.CharField(max_length=255, blank=True)
    parent_test = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="retests"
    )
    attempt_number = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=DRAFT)

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


class Question(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name="questions")
    order_index = models.PositiveIntegerField(default=0)
    text = models.TextField()
    image = models.ImageField(upload_to="questions/", null=True, blank=True)
    topic = models.CharField(max_length=255, blank=True)
    difficulty = models.CharField(max_length=20, blank=True)

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
