from django.db.models import Sum
from django.utils import timezone

from certification.models import Certification, ComplianceItem, CorrectiveAction
from certification.services import aggregate_readiness, visible_certifications
from farms.land import missing_land_use_years
from farms.scope import scoped_farmers, scoped_farms, scoped_fields
from inspections.models import Inspection
from inventory.models import InputProduct
from inventory.services import on_hand
from ndvi.models import Observation
from production.models import Activity, Harvest


def build_dashboard(user, membership):
    farmers = scoped_farmers(user, membership)
    farms = scoped_farms(user, membership)
    fields = scoped_fields(user, membership)
    certifications = list(
        visible_certifications(user, membership)
        .select_related("standard", "farmer")
        .prefetch_related("items__requirement")
    )
    official = [
        {
            "id": str(row.id),
            "standard": row.standard.code,
            "status": row.status,
            "farmer": row.farmer.display_name if row.farmer_id else None,
            "certificate_number": row.certificate_number,
            "expires_on": row.expires_on,
        }
        for row in certifications
        if row.status == Certification.Status.CERTIFIED
    ]
    harvest_kg = Harvest.objects.filter(farm__in=farms).aggregate(total=Sum("quantity_kg"))["total"]
    activities = Activity.objects.filter(farm__in=farms).select_related("farm").order_by(
        "-occurred_on", "-created_at"
    )[:8]
    upcoming = Inspection.objects.filter(
        organization=membership.organization,
        farm__in=farms,
        status=Inspection.Status.SCHEDULED,
        scheduled_for__gte=timezone.now(),
    ).select_related("farm")[:5]
    actions = CorrectiveAction.objects.filter(
        certification__in=certifications,
        status=CorrectiveAction.Status.OPEN,
    ).order_by("due_on")[:8]
    ndvi = []
    for field in fields:
        points = [
            {
                "date": row.observed_on,
                "ndvi_mean": row.ndvi_mean,
                "source": row.source,
            }
            for row in field.observations.order_by("observed_on")
        ]
        if points:
            ndvi.append({"field_id": str(field.id), "field_name": field.name, "points": points})
    recommendations = []
    missing_items = ComplianceItem.objects.filter(
        certification__in=certifications,
        state=ComplianceItem.State.MISSING,
    ).select_related("requirement")[:5]
    for item in missing_items:
        recommendations.append(
            {
                "text": f"Add evidence for {item.requirement.title}.",
                "basis": "missing",
                "source": "compliance",
            }
        )
    for field in fields:
        years = missing_land_use_years(field)
        if years and len(recommendations) < 8:
            recommendations.append(
                {
                    "text": (
                        f"Add land-use history for {field.name}: "
                        + ", ".join(str(year) for year in years)
                        + "."
                    ),
                    "basis": "missing",
                    "source": "land_use",
                }
            )
    for product in InputProduct.objects.filter(organization=membership.organization):
        quantity = on_hand(product)
        if product.reorder_level and quantity <= product.reorder_level and len(recommendations) < 8:
            recommendations.append(
                {
                    "text": f"Restock {product.name}. On hand is {quantity} {product.unit}.",
                    "basis": "calculated",
                    "source": "inventory",
                }
            )
    if not farms.exists() and len(recommendations) < 8:
        recommendations.append(
            {
                "text": "Add a farmer and a farm so field records have a home.",
                "basis": "missing",
                "source": "setup",
            }
        )
    return {
        "farmers": farmers.count(),
        "farms": farms.count(),
        "fields": fields.count(),
        "certification": {
            **aggregate_readiness(certifications),
            "official": official,
        },
        "production": {
            "harvest_kg": harvest_kg or 0,
            "activity_count": Activity.objects.filter(farm__in=farms).count(),
        },
        "ndvi": ndvi,
        "satellite_observations": Observation.objects.filter(
            field__in=fields,
            source=Observation.Source.SATELLITE,
        ).count(),
        "recent_activities": [
            {
                "id": str(row.id),
                "kind": row.kind,
                "occurred_on": row.occurred_on,
                "farm": row.farm.name,
                "notes": row.notes,
            }
            for row in activities
        ],
        "upcoming_inspections": [
            {
                "id": str(row.id),
                "farm": row.farm.name,
                "scheduled_for": row.scheduled_for,
                "status": row.status,
            }
            for row in upcoming
        ],
        "pending_actions": [
            {
                "id": str(row.id),
                "title": row.title,
                "due_on": row.due_on,
                "status": row.status,
            }
            for row in actions
        ],
        "recommendations": recommendations,
    }
