import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify


class Organization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=80, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:80] or "organization"
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class Membership(models.Model):
    class Role(models.TextChoices):
        ORG_ADMIN = "org_admin", "Organization admin"
        MANAGER = "manager", "Manager"
        FARMER = "farmer", "Farmer"
        INSPECTOR = "inspector", "Inspector"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(max_length=32, choices=Role.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "organization"],
                name="uniq_membership_user_organization",
            )
        ]
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.user} @ {self.organization} ({self.role})"


class Farmer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="farmers",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="farmer_profiles",
    )
    farmer_id = models.CharField(max_length=64)
    display_name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "farmer_id"],
                name="uniq_farmer_id_per_organization",
            )
        ]
        ordering = ["display_name"]

    def clean(self):
        if self.farmer_id:
            self.farmer_id = self.farmer_id.strip().upper()
        if self.user_id and self.user.farmer_id and self.farmer_id != self.user.farmer_id:
            raise ValidationError({"farmer_id": "FarmerID must match the linked user's FarmerID."})

    def save(self, *args, **kwargs):
        if self.farmer_id:
            self.farmer_id = self.farmer_id.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.display_name} ({self.farmer_id})"
