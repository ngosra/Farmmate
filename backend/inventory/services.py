from decimal import Decimal

from rest_framework.exceptions import ValidationError

from certification.models import Certification
from inventory.models import InputApproval, StockMovement


def on_hand(product) -> Decimal:
    total = Decimal("0")
    for kind, quantity in product.movements.values_list("kind", "quantity"):
        if kind == StockMovement.Kind.OUT:
            total -= quantity
        else:
            total += quantity
    return total


def approval_flags(organization, product):
    standard_ids = (
        Certification.objects.filter(organization=organization)
        .exclude(status=Certification.Status.WITHDRAWN)
        .values_list("standard_id", flat=True)
    )
    rows = InputApproval.objects.filter(product=product,
        standard_id__in=standard_ids).select_related(
        "standard"
    )
    return [
        {"standard": row.standard.code, "status": row.status, "note": row.note}
        for row in rows
    ]


def assert_can_use(organization, product):
    flags = approval_flags(organization, product)
    prohibited = [flag for flag in flags if flag["status"] == InputApproval.Status.PROHIBITED]
    if prohibited:
        codes = ", ".join(flag["standard"] for flag in prohibited)
        raise ValidationError({"product": f"This input is prohibited for {codes}."})
    return flags
