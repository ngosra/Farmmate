from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from traceability.models import Batch, BatchInput, Movement, new_public_code

CONSUMING = {Movement.Kind.PROCESS, Movement.Kind.SHIP}


def sourced_kg(batch) -> Decimal:
    return BatchInput.objects.filter(batch=batch).aggregate(total=Sum("quantity_kg"))[
        "total"
    ] or Decimal("0")


def remaining_kg(batch) -> Decimal:
    loss = batch.movements.aggregate(total=Sum("loss_kg"))["total"] or Decimal("0")
    consumed = (
        batch.movements.filter(kind__in=CONSUMING).aggregate(total=Sum("quantity_kg"))["total"]
        or Decimal("0")
    )
    return sourced_kg(batch) - loss - consumed


def balance(batch):
    sourced = sourced_kg(batch)
    remaining = remaining_kg(batch)
    return {
        "sourced_kg": sourced,
        "remaining_kg": remaining,
        "balanced": remaining >= 0,
        "note": (
            "Remaining quantity is sourced harvest minus processing, shipments, and recorded loss. "
            "Storage and transport do not consume quantity unless a loss is entered."
        ),
    }


def harvest_available(harvest) -> Decimal:
    used = BatchInput.objects.filter(harvest=harvest).aggregate(total=Sum("quantity_kg"))[
        "total"
    ] or Decimal("0")
    return harvest.quantity_kg - used


def allocate_code(organization) -> str:
    year = timezone.now().year
    prefix = f"B-{year}-"
    count = Batch.objects.filter(organization=organization, code__startswith=prefix).count()
    return f"{prefix}{count + 1:04d}"


def open_batch(*, organization, user, product_name, inputs):
    if not inputs:
        raise ValidationError({"inputs": "Add at least one harvest."})
    with transaction.atomic():
        checked = []
        for row in inputs:
            harvest = row["harvest"]
            quantity = row["quantity_kg"]
            if harvest.organization_id != organization.id:
                raise ValidationError({"inputs": "Harvest was not found in your organization."})
            if quantity <= 0:
                raise ValidationError({"inputs": "Quantity must be greater than zero."})
            available = harvest_available(harvest)
            if quantity > available:
                raise ValidationError(
                    {
                        "inputs": (
                            f"Only {available} kg of harvest {harvest.id} is still unallocated."
                        )
                    }
                )
            checked.append((harvest, quantity))
        batch = None
        for _attempt in range(5):
            candidate = Batch(
                organization=organization,
                product_name=product_name.strip(),
                code=allocate_code(organization),
                public_code=new_public_code(),
                created_by=user,
            )
            try:
                with transaction.atomic():
                    candidate.save()
                batch = candidate
                break
            except IntegrityError:
                continue
        if batch is None:
            raise ValidationError({"code": "Could not allocate a batch code."})
        for harvest, quantity in checked:
            BatchInput.objects.create(batch=batch, harvest=harvest, quantity_kg=quantity)
        return batch


def add_movement(batch, user, data):
    kind = data["kind"]
    quantity = data.get("quantity_kg") or Decimal("0")
    loss = data.get("loss_kg") or Decimal("0")
    if quantity < 0 or loss < 0:
        raise ValidationError("Quantities cannot be negative.")
    if kind in CONSUMING and quantity <= 0:
        raise ValidationError({"quantity_kg": "Enter the quantity that leaves the batch."})
    extra = loss + (quantity if kind in CONSUMING else Decimal("0"))
    with transaction.atomic():
        locked = Batch.objects.select_for_update().get(pk=batch.pk)
        if remaining_kg(locked) - extra < 0:
            raise ValidationError(
                {"quantity_kg": "This movement is larger than the quantity still in the batch."}
            )
        return Movement.objects.create(
            batch=locked,
            kind=kind,
            quantity_kg=quantity,
            loss_kg=loss,
            happened_on=data["happened_on"],
            location=data.get("location", ""),
            notes=data.get("notes", ""),
            recorded_by=user,
        )
