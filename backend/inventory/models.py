from django.conf import settings
from django.db import models

from organizations.models import Organization
from records import UUIDModel


class Supplier(UUIDModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="suppliers"
    )
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=40, blank=True)
    region = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"], name="uniq_supplier_name_per_org"
            )
        ]

    def __str__(self) -> str:
        return self.name


class InputProduct(UUIDModel):
    class Category(models.TextChoices):
        SEED = "seed", "Seed"
        FERTILIZER = "fertilizer", "Fertilizer"
        PESTICIDE = "pesticide", "Pesticide"
        OTHER = "other", "Other"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="input_products"
    )
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=Category.choices)
    unit = models.CharField(max_length=24, default="kg")
    reorder_level = models.DecimalField(max_digits=12, decimal_places=3, default=0)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"], name="uniq_input_name_per_org"
            )
        ]

    def __str__(self) -> str:
        return self.name


class InputApproval(UUIDModel):
    class Status(models.TextChoices):
        APPROVED = "approved", "Approved"
        RESTRICTED = "restricted", "Restricted"
        PROHIBITED = "prohibited", "Prohibited"

    product = models.ForeignKey(InputProduct, on_delete=models.CASCADE, related_name="approvals")
    standard = models.ForeignKey(
        "certification.Standard", on_delete=models.CASCADE, related_name="input_approvals"
    )
    status = models.CharField(max_length=16, choices=Status.choices)
    note = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product", "standard"], name="uniq_input_approval_standard"
            )
        ]

    def __str__(self) -> str:
        return f"{self.product} / {self.standard.code}: {self.status}"


class StockMovement(UUIDModel):
    class Kind(models.TextChoices):
        IN = "in", "In"
        OUT = "out", "Out"
        ADJUSTMENT = "adjustment", "Adjustment"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="stock_movements"
    )
    product = models.ForeignKey(InputProduct, on_delete=models.PROTECT, related_name="movements")
    supplier = models.ForeignKey(
        Supplier, null=True, blank=True, on_delete=models.SET_NULL, related_name="movements"
    )
    activity = models.ForeignKey(
        "production.Activity",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="stock_movements",
    )
    kind = models.CharField(max_length=16, choices=Kind.choices)
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    occurred_on = models.DateField()
    reference = models.CharField(max_length=80, blank=True)
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="stock_movements",
    )

    class Meta:
        ordering = ["-occurred_on", "-created_at"]
        indexes = [models.Index(fields=["organization", "occurred_on"])]

    def __str__(self) -> str:
        return f"{self.kind} {self.quantity} {self.product}"
