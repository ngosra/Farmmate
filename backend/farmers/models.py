from django.conf import settings
from django.db import models

from organizations.models import Farmer
from records import UUIDModel


def identification_upload(instance, filename):
    name = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    return f"identification/{instance.farmer.organization_id}/{instance.farmer_id}/{name}"


class FarmerDeclaration(UUIDModel):
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name="declarations")
    title = models.CharField(max_length=200)
    statement = models.TextField()
    declared_on = models.DateField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="farmer_declarations",
    )

    class Meta:
        ordering = ["-declared_on", "-created_at"]

    def __str__(self) -> str:
        return self.title


class Identification(UUIDModel):
    class Kind(models.TextChoices):
        NATIONAL_ID = "national_id", "National ID"
        COOPERATIVE_CARD = "cooperative_card", "Cooperative card"
        OTHER = "other", "Other"

    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name="identifications")
    kind = models.CharField(max_length=32, choices=Kind.choices, default=Kind.OTHER)
    number = models.CharField(max_length=80)
    file = models.FileField(upload_to=identification_upload, null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.kind} {self.number}"
