from django.conf import settings
from django.db import models

from crops.models import Crop, Planting
from farms.models import Farm, Field
from organizations.models import Farmer, Organization
from records import UUIDModel


class Activity(UUIDModel):
    class Kind(models.TextChoices):
        PLANTING = "planting", "Planting"
        WEEDING = "weeding", "Weeding"
        SPRAYING = "spraying", "Spraying"
        FERTILIZING = "fertilizing", "Fertilizing"
        HARVEST = "harvest", "Harvest"
        OTHER = "other", "Other"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="activities"
    )
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="activities")
    field = models.ForeignKey(
        Field, null=True, blank=True, on_delete=models.CASCADE, related_name="activities"
    )
    farmer = models.ForeignKey(
        Farmer, null=True, blank=True, on_delete=models.SET_NULL, related_name="activities"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="activities",
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    occurred_on = models.DateField()
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-occurred_on", "-created_at"]
        indexes = [models.Index(fields=["organization", "occurred_on"])]

    def __str__(self) -> str:
        return f"{self.kind} on {self.occurred_on}"


class Harvest(UUIDModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="harvests"
    )
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="harvests")
    field = models.ForeignKey(Field, on_delete=models.PROTECT, related_name="harvests")
    planting = models.ForeignKey(
        Planting, null=True, blank=True, on_delete=models.SET_NULL, related_name="harvests"
    )
    crop = models.ForeignKey(
        Crop, null=True, blank=True, on_delete=models.PROTECT, related_name="harvests"
    )
    harvested_on = models.DateField()
    quantity_kg = models.DecimalField(max_digits=12, decimal_places=3)
    quality = models.CharField(max_length=80, blank=True)
    storage_location = models.CharField(max_length=160, blank=True)
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="harvests",
    )

    class Meta:
        ordering = ["-harvested_on", "-created_at"]
        indexes = [models.Index(fields=["organization", "harvested_on"])]

    def __str__(self) -> str:
        return f"{self.quantity_kg} kg on {self.harvested_on}"


class StorageRecord(UUIDModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="storage_records"
    )
    harvest = models.ForeignKey(
        Harvest, null=True, blank=True, on_delete=models.SET_NULL, related_name="storage_records"
    )
    location = models.CharField(max_length=160)
    quantity_kg = models.DecimalField(max_digits=12, decimal_places=3)
    stored_on = models.DateField()
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-stored_on"]

    def __str__(self) -> str:
        return f"{self.quantity_kg} kg at {self.location}"
