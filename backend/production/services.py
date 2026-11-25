from decimal import ROUND_HALF_UP, Decimal

from production.models import Harvest


def yield_rows(fields):
    totals = {}
    for field_id, quantity in Harvest.objects.filter(field__in=fields).values_list(
        "field_id", "quantity_kg"
    ):
        totals[field_id] = totals.get(field_id, Decimal("0")) + quantity
    rows = []
    for field in fields:
        quantity = totals.get(field.id, Decimal("0"))
        area = field.area_hectares
        per_hectare = None
        if area is not None and area > 0:
            per_hectare = (quantity / area).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        rows.append(
            {
                "field_id": str(field.id),
                "field_name": field.name,
                "farm_id": str(field.farm_id),
                "farm_name": field.farm.name,
                "quantity_kg": quantity,
                "area_hectares": area,
                "kg_per_hectare": per_hectare,
            }
        )
    return rows
