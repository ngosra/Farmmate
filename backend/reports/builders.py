import csv
import io

from django.http import HttpResponse

from certification.models import ComplianceItem
from certification.services import readiness
from farms.scope import scoped_farms, scoped_fields
from inventory.models import InputProduct
from inventory.services import on_hand
from production.models import Harvest
from production.services import yield_rows
from traceability.models import Batch
from traceability.services import balance


def _text(value):
    if value is None:
        return ""
    return str(value)


def farm_rows(user, membership):
    rows = []
    for farm in scoped_farms(user, membership):
        rows.append(
            {
                "name": farm.name,
                "code": farm.code,
                "farmer": farm.farmer.display_name,
                "farmer_id": farm.farmer.farmer_id,
                "region": farm.region,
                "latitude": _text(farm.latitude),
                "longitude": _text(farm.longitude),
                "status": farm.status,
                "surveyed_hectares": _text(farm.area_hectares),
            }
        )
    return rows


def production_rows(user, membership):
    farms = scoped_farms(user, membership)
    rows = []
    for harvest in Harvest.objects.filter(farm__in=farms).select_related("farm", "field", "crop"):
        rows.append(
            {
                "harvested_on": harvest.harvested_on.isoformat(),
                "farm": harvest.farm.name,
                "field": harvest.field.name,
                "crop": str(harvest.crop) if harvest.crop_id else "",
                "quantity_kg": _text(harvest.quantity_kg),
                "quality": harvest.quality,
                "storage_location": harvest.storage_location,
            }
        )
    return rows


def yield_report(user, membership):
    rows = []
    for row in yield_rows(scoped_fields(user, membership)):
        rows.append({key: _text(value) for key, value in row.items()})
    return rows


def inventory_rows(membership):
    rows = []
    for product in InputProduct.objects.filter(organization=membership.organization):
        rows.append(
            {
                "name": product.name,
                "category": product.category,
                "unit": product.unit,
                "on_hand": _text(on_hand(product)),
                "reorder_level": _text(product.reorder_level),
            }
        )
    return rows


def compliance_rows(user, membership):
    from certification.services import visible_certifications

    rows = []
    for certification in visible_certifications(user, membership).select_related("standard"):
        score = readiness(certification)
        items = ComplianceItem.objects.filter(certification=certification).select_related(
            "requirement"
        )
        for item in items:
            rows.append(
                {
                    "standard": certification.standard.code,
                    "official_status": certification.status,
                    "readiness_percent": _text(score["readiness_percent"]),
                    "requirement": item.requirement.title,
                    "state": item.state,
                    "weight": item.requirement.weight,
                }
            )
    return rows


def trace_rows(batch):
    row = balance(batch)
    movements = [
        {
            "batch": batch.code,
            "kind": movement.kind,
            "happened_on": movement.happened_on.isoformat(),
            "quantity_kg": _text(movement.quantity_kg),
            "loss_kg": _text(movement.loss_kg),
            "location": movement.location,
            "sourced_kg": _text(row["sourced_kg"]),
            "remaining_kg": _text(row["remaining_kg"]),
        }
        for movement in batch.movements.all()
    ]
    if movements:
        return movements
    return [
        {
            "batch": batch.code,
            "kind": "",
            "happened_on": "",
            "quantity_kg": "",
            "loss_kg": "",
            "location": "",
            "sourced_kg": _text(row["sourced_kg"]),
            "remaining_kg": _text(row["remaining_kg"]),
        }
    ]


def csv_response(filename, rows):
    headers = list(rows[0].keys()) if rows else ["none"]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=headers)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    response = HttpResponse(buffer.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def batch_for(membership, batch_id):
    return Batch.objects.filter(organization=membership.organization, pk=batch_id).first()
