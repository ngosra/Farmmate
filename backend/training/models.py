from django.db import models

from organizations.models import Organization
from records import UUIDModel


def material_upload(instance, filename):
    name = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    return f"training/{instance.session.organization_id}/{instance.session_id}/{name}"


class TrainingSession(UUIDModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="training_sessions"
    )
    title = models.CharField(max_length=200)
    held_on = models.DateField()
    location = models.CharField(max_length=160, blank=True)
    trainer_name = models.CharField(max_length=160, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-held_on"]

    def __str__(self) -> str:
        return self.title


class TrainingMaterial(UUIDModel):
    session = models.ForeignKey(
        TrainingSession, on_delete=models.CASCADE, related_name="materials"
    )
    title = models.CharField(max_length=200)
    link = models.URLField(blank=True)
    file = models.FileField(upload_to=material_upload, null=True, blank=True)

    class Meta:
        ordering = ["title"]

    def __str__(self) -> str:
        return self.title


class Attendance(UUIDModel):
    session = models.ForeignKey(TrainingSession, on_delete=models.CASCADE,
        related_name="attendance")
    farmer = models.ForeignKey(
        "organizations.Farmer", on_delete=models.CASCADE, related_name="attendance"
    )
    present = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["session", "farmer"], name="uniq_training_attendance")
        ]

    def __str__(self) -> str:
        return f"{self.farmer} @ {self.session}"
