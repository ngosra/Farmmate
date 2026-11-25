from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from api.roles import CERT_DECIDE
from certification.models import Certification, ComplianceItem, Reminder
from organizations.models import Membership

OFFICIAL = {
    Certification.Status.CERTIFIED,
    Certification.Status.SUSPENDED,
    Certification.Status.EXPIRED,
    Certification.Status.WITHDRAWN,
}
FARMER_STATUSES = {Certification.Status.PREPARING, Certification.Status.SUBMITTED}
STAFF_STATUSES = FARMER_STATUSES | {Certification.Status.UNDER_REVIEW}
FARMER_ITEM_STATES = {
    ComplianceItem.State.MISSING,
    ComplianceItem.State.DECLARED,
    ComplianceItem.State.EVIDENCE,
}
OFFICER_ITEM_STATES = {
    ComplianceItem.State.VERIFIED,
    ComplianceItem.State.NOT_APPLICABLE,
}


def visible_certifications(user, membership):
    queryset = Certification.objects.filter(organization=membership.organization)
    if membership.role == Membership.Role.FARMER and not user.is_superuser:
        queryset = queryset.filter(
            Q(farmer__user=user)
            | Q(farm__farmer__user=user)
            | Q(farmer__isnull=True, farm__isnull=True)
        )
    return queryset


def open_certification(*, organization, standard, actor, farmer=None, farm=None):
    if standard.organization_id not in (None, organization.id):
        raise ValidationError(
            {"standard_id": "That standard is not available to this organization."}
        )
    if farmer and farmer.organization_id != organization.id:
        raise ValidationError({"farmer": "Farmer was not found in your organization."})
    if farm and farm.organization_id != organization.id:
        raise ValidationError({"farm": "Farm was not found in your organization."})
    if farm and farmer and farm.farmer_id != farmer.id:
        raise ValidationError({"farm": "That farm belongs to a different farmer."})
    if not standard.requirements.exists():
        raise ValidationError({"standard_id": "This standard has no requirements yet."})
    with transaction.atomic():
        certification = Certification.objects.create(
            organization=organization,
            standard=standard,
            farmer=farmer,
            farm=farm,
        )
        ComplianceItem.objects.bulk_create(
            [
                ComplianceItem(
                    certification=certification,
                    requirement=requirement,
                    state=ComplianceItem.State.MISSING,
                    updated_by=actor,
                )
                for requirement in standard.requirements.all()
            ]
        )
    return certification


def _percent(part, whole):
    if not whole:
        return None
    value = (Decimal(part) / Decimal(whole) * Decimal(100)).quantize(
        Decimal("0.1"),
        rounding=ROUND_HALF_UP,
    )
    return float(value)


def readiness(certification):
    items = list(certification.items.select_related("requirement"))
    applicable = [item for item in items if item.state != ComplianceItem.State.NOT_APPLICABLE]
    weight = sum(item.requirement.weight for item in applicable)
    verified = sum(
        item.requirement.weight
        for item in applicable
        if item.state == ComplianceItem.State.VERIFIED
    )
    declared = sum(
        item.requirement.weight
        for item in applicable
        if item.state in {ComplianceItem.State.DECLARED, ComplianceItem.State.EVIDENCE}
    )
    missing = sum(
        item.requirement.weight
        for item in applicable
        if item.state == ComplianceItem.State.MISSING
    )
    return {
        "readiness_percent": _percent(verified, weight),
        "formula": "verified requirement weight / applicable requirement weight",
        "verified_weight": verified,
        "declared_weight": declared,
        "missing_weight": missing,
        "applicable_weight": weight,
        "counts": {
            "verified": sum(1 for item in applicable if item.state ==
                ComplianceItem.State.VERIFIED),
            "declared": sum(1 for item in applicable if item.state ==
                ComplianceItem.State.DECLARED),
            "evidence_attached": sum(
                1 for item in applicable if item.state == ComplianceItem.State.EVIDENCE
            ),
            "missing": sum(1 for item in applicable if item.state == ComplianceItem.State.MISSING),
            "not_applicable": sum(
                1 for item in items if item.state == ComplianceItem.State.NOT_APPLICABLE
            ),
        },
        "official_status": certification.status,
        "is_official_certification": certification.status == Certification.Status.CERTIFIED,
        "message": (
            "Readiness counts only verified evidence. "
            "A high score is not an official certification."
        ),
    }


def aggregate_readiness(certifications):
    verified = 0
    applicable = 0
    missing = 0
    declared = 0
    for certification in certifications:
        row = readiness(certification)
        verified += row["verified_weight"]
        applicable += row["applicable_weight"]
        missing += row["missing_weight"]
        declared += row["declared_weight"]
    return {
        "readiness_percent": _percent(verified, applicable),
        "verified_weight": verified,
        "declared_weight": declared,
        "missing_weight": missing,
        "applicable_weight": applicable,
        "message": (
            "Readiness counts only verified evidence. "
            "A high score is not an official certification."
        ),
    }


def set_decision(certification, *, status, actor, membership, **fields):
    if membership.role == Membership.Role.FARMER and not actor.is_superuser:
        if status not in FARMER_STATUSES:
            raise PermissionDenied("You can submit a certification, not decide it.")
    elif status in OFFICIAL and membership.role not in CERT_DECIDE and not actor.is_superuser:
        raise PermissionDenied(
            "Only a certification officer or organization admin can record this decision."
        )
    elif status not in STAFF_STATUSES | OFFICIAL:
        raise ValidationError({"status": "Unknown certification status."})
    if status == Certification.Status.CERTIFIED and not (
        fields.get("certificate_number") or certification.certificate_number
    ):
        raise ValidationError(
            {"certificate_number": "An official certificate number is required."}
        )
    certification.status = status
    for name in ("certificate_number", "issued_on", "expires_on", "decision_notes"):
        if name in fields and fields[name] is not None:
            setattr(certification, name, fields[name])
    if status in OFFICIAL:
        certification.decided_by = actor
    certification.save()
    return certification


def set_item_state(item, *, state, actor, membership, note=None):
    officer = membership.role in CERT_DECIDE or actor.is_superuser
    if state in OFFICER_ITEM_STATES and not officer:
        raise PermissionDenied(
            "Only a certification officer can verify evidence or mark it not applicable."
        )
    if membership.role == Membership.Role.FARMER and state not in FARMER_ITEM_STATES:
        raise PermissionDenied("You can declare information or attach evidence.")
    if state not in ComplianceItem.State.values:
        raise ValidationError({"state": "Unknown compliance state."})
    item.state = state
    if note is not None:
        item.note = note
    item.updated_by = actor
    item.save()
    return item


def create_expiry_reminders(today=None):
    today = today or timezone.localdate()
    horizon = today + timedelta(days=30)
    queryset = Certification.objects.filter(
        status=Certification.Status.CERTIFIED,
        expires_on__isnull=False,
        expires_on__gte=today,
        expires_on__lte=horizon,
    ).select_related("standard")
    created = 0
    for certification in queryset:
        _row, was_created = Reminder.objects.get_or_create(
            certification=certification,
            kind=Reminder.Kind.EXPIRY,
            due_on=certification.expires_on,
            defaults={
                "organization": certification.organization,
                "message": (
                    f"{certification.standard.code} certificate "
                    f"{certification.certificate_number or certification.id} "
                    f"expires on {certification.expires_on}."
                ),
            },
        )
        created += int(was_created)
    return created
