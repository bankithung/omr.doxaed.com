from django.conf import settings
from django.db import models

from common.encryption import EncryptedTextField
from common.models import OwnerScopedModel, UUIDModel


class Roster(OwnerScopedModel):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="+",
    )
    class_group = models.ForeignKey(
        "assessments.ClassGroup",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="rosters",
    )
    name = models.CharField(max_length=255)

    class Meta(OwnerScopedModel.Meta):
        ordering = ["name", "id"]

    def __str__(self):
        return self.name


class Student(UUIDModel):
    roster = models.ForeignKey(Roster, on_delete=models.CASCADE, related_name="students")
    full_name = EncryptedTextField(blank=True, default="")
    roll_number = models.CharField(max_length=32)
    external_ref = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        ordering = ["roll_number", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["roster", "roll_number"],
                name="uniq_roll_per_roster",
            )
        ]

    def __str__(self):
        return f"{self.roll_number} – {self.roster}"
