import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify


class Organization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=80, unique=True, blank=True)
    country = models.CharField(max_length=80, blank=True)
    region = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = (slugify(self.name)[:70] or "organization")
            slug = base
            number = 2
            while Organization.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                suffix = f"-{number}"
                slug = f"{base[: 80 - len(suffix)]}{suffix}"
                number += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class Membership(models.Model):
    class Role(models.TextChoices):
        ORG_ADMIN = "org_admin", "Organization admin"
        FIELD_OFFICER = "field_officer", "Field officer"
        MANAGER = "manager", "Farm manager"
        FARMER = "farmer", "Farmer"
        INSPECTOR = "inspector", "Inspector"
        CERTIFICATION_OFFICER = "certification_officer", "Certification officer"

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
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    national_id = models.CharField(max_length=64, blank=True)
    region = models.CharField(max_length=120, blank=True)
    community = models.CharField(max_length=120, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "farmer_id"],
                name="uniq_farmer_id_per_organization",
            )
        ]
        ordering = ["display_name"]
        indexes = [models.Index(fields=["organization", "display_name"])]

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


class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="audit_logs",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=32)
    entity_type = models.CharField(max_length=80)
    entity_id = models.CharField(max_length=64, blank=True)
    summary = models.CharField(max_length=240)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["organization", "created_at"])]

    def __str__(self) -> str:
        return self.summary
