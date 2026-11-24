import secrets

from django.conf import settings
from django.db import models

from organizations.models import Organization
from records import UUIDModel


def new_public_code() -> str:
    return secrets.token_urlsafe(9)


class Batch(UUIDModel):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        SEALED = "sealed", "Sealed"
        SHIPPED = "shipped", "Shipped"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="batches")
    code = models.CharField(max_length=40)
    public_code = models.CharField(max_length=32, unique=True, default=new_public_code)
    product_name = models.CharField(max_length=200)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="batches",
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "code"], name="uniq_batch_code_per_org")
        ]

    def __str__(self) -> str:
        return self.code


class BatchInput(UUIDModel):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name="inputs")
    harvest = models.ForeignKey(
        "production.Harvest", on_delete=models.PROTECT, related_name="batch_inputs"
    )
    quantity_kg = models.DecimalField(max_digits=12, decimal_places=3)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.quantity_kg} kg"


class Movement(UUIDModel):
    class Kind(models.TextChoices):
        STORE = "store", "Store"
        PROCESS = "process", "Process"
        TRANSPORT = "transport", "Transport"
        SHIP = "ship", "Ship"

    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name="movements")
    kind = models.CharField(max_length=16, choices=Kind.choices)
    quantity_kg = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    loss_kg = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    happened_on = models.DateField()
    location = models.CharField(max_length=160, blank=True)
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="batch_movements",
    )

    class Meta:
        ordering = ["happened_on", "created_at"]

    def __str__(self) -> str:
        return f"{self.kind} {self.quantity_kg} kg"
