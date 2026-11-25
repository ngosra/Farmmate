from django.conf import settings
from django.db import models

from records import UUIDModel


class Observation(UUIDModel):
    class Source(models.TextChoices):
        MANUAL = "manual", "Manual"
        SATELLITE = "satellite", "Satellite"

    field = models.ForeignKey(
        "farms.Field", on_delete=models.CASCADE, related_name="observations"
    )
    observed_on = models.DateField()
    ndvi_mean = models.DecimalField(max_digits=5, decimal_places=4)
    source = models.CharField(max_length=16, choices=Source.choices)
    provider = models.CharField(max_length=80, blank=True)
    external_id = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ndvi_observations",
    )

    class Meta:
        ordering = ["observed_on"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(ndvi_mean__gte=-1) & models.Q(ndvi_mean__lte=1),
                name="ndvi_mean_between_minus_one_and_one",
            )
        ]
        indexes = [models.Index(fields=["field", "observed_on"])]

    def __str__(self) -> str:
        return f"{self.observed_on} {self.ndvi_mean} ({self.source})"
