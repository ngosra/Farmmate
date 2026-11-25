from django.conf import settings
from django.contrib.gis.db.models import PointField, PolygonField
from django.db import models

from organizations.models import Farmer, Organization
from records import UUIDModel


def farm_file_upload(instance, filename):
    name = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    return f"farms/{instance.farm.organization_id}/{instance.farm_id}/{name}"


class Farm(UUIDModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="farms")
    farmer = models.ForeignKey(Farmer, on_delete=models.PROTECT, related_name="farms")
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=40)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location = PointField(srid=4326, null=True, blank=True)
    country = models.CharField(max_length=80, blank=True)
    region = models.CharField(max_length=120, blank=True)
    district = models.CharField(max_length=120, blank=True)
    community = models.CharField(max_length=120, blank=True)
    area_hectares = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    established_year = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "code"], name="uniq_farm_code_per_org")
        ]
        indexes = [models.Index(fields=["organization", "name"])]

    def save(self, *args, **kwargs):
        if self.latitude is not None and self.longitude is not None:
            from django.contrib.gis.geos import Point

            self.location = Point(float(self.longitude), float(self.latitude), srid=4326)
        else:
            self.location = None
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class Field(UUIDModel):
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="fields")
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=40)
    boundary = PolygonField(srid=4326, null=True, blank=True)
    area_hectares = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    soil_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["farm", "code"], name="uniq_field_code_per_farm")
        ]

    def __str__(self) -> str:
        return self.name


class LandUse(UUIDModel):
    field = models.ForeignKey(Field, on_delete=models.CASCADE, related_name="land_uses")
    year = models.PositiveIntegerField()
    use = models.CharField(max_length=160)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-year"]
        constraints = [
            models.UniqueConstraint(fields=["field", "year"], name="uniq_land_use_year")
        ]

    def __str__(self) -> str:
        return f"{self.year}: {self.use}"


class FarmDocument(UUIDModel):
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="documents")
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to=farm_file_upload)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="farm_documents",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title
