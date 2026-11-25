from django.db import models

from farms.models import Field
from organizations.models import Organization
from records import UUIDModel


class Crop(UUIDModel):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="crops")
    name = models.CharField(max_length=120)
    variety = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ["name", "variety"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name", "variety"],
                name="uniq_crop_name_variety",
            )
        ]

    def __str__(self) -> str:
        if self.variety:
            return f"{self.name} ({self.variety})"
        return self.name


class Planting(UUIDModel):
    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        PLANTED = "planted", "Planted"
        HARVESTED = "harvested", "Harvested"
        FAILED = "failed", "Failed"

    field = models.ForeignKey(Field, on_delete=models.CASCADE, related_name="plantings")
    crop = models.ForeignKey(Crop, on_delete=models.PROTECT, related_name="plantings")
    season_year = models.PositiveIntegerField()
    planted_on = models.DateField(null=True, blank=True)
    expected_harvest_on = models.DateField(null=True, blank=True)
    area_hectares = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PLANNED)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-season_year", "crop__name"]

    def __str__(self) -> str:
        return f"{self.crop} {self.season_year}"
