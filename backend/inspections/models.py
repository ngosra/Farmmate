from django.conf import settings
from django.db import models

from organizations.models import Organization
from records import UUIDModel


class Inspection(UUIDModel):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="inspections"
    )
    farm = models.ForeignKey("farms.Farm", on_delete=models.PROTECT, related_name="inspections")
    certification = models.ForeignKey(
        "certification.Certification",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="inspections",
    )
    inspector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="inspections",
    )
    scheduled_for = models.DateTimeField()
    completed_on = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)
    summary = models.TextField(blank=True)

    class Meta:
        ordering = ["scheduled_for"]
        indexes = [models.Index(fields=["organization", "scheduled_for"])]

    def __str__(self) -> str:
        return f"Inspection {self.scheduled_for:%Y-%m-%d}"


class InspectionCheck(UUIDModel):
    class Result(models.TextChoices):
        PENDING = "pending", "Pending"
        PASS = "pass", "Pass"
        FAIL = "fail", "Fail"
        NOT_APPLICABLE = "not_applicable", "Not applicable"

    inspection = models.ForeignKey(Inspection, on_delete=models.CASCADE, related_name="checks")
    prompt = models.CharField(max_length=240)
    requirement = models.ForeignKey(
        "certification.Requirement",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="inspection_checks",
    )
    result = models.CharField(max_length=20, choices=Result.choices, default=Result.PENDING)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return self.prompt
