from django.conf import settings
from django.db import models

from organizations.models import Organization
from records import UUIDModel


def evidence_upload(instance, filename):
    name = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    org_id = instance.item.certification.organization_id
    return f"evidence/{org_id}/{instance.item_id}/{name}"


class Standard(UUIDModel):
    organization = models.ForeignKey(
        Organization,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="standards",
    )
    code = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=160)
    authority = models.CharField(max_length=160, blank=True)
    summary = models.TextField(blank=True)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return self.code


class Requirement(UUIDModel):
    standard = models.ForeignKey(Standard, on_delete=models.CASCADE, related_name="requirements")
    code = models.CharField(max_length=40)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    weight = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(fields=["standard", "code"], name="uniq_requirement_code")
        ]

    def __str__(self) -> str:
        return f"{self.standard.code}:{self.code}"


class Certification(UUIDModel):
    class Status(models.TextChoices):
        PREPARING = "preparing", "Preparing"
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under review"
        CERTIFIED = "certified", "Certified"
        SUSPENDED = "suspended", "Suspended"
        EXPIRED = "expired", "Expired"
        WITHDRAWN = "withdrawn", "Withdrawn"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="certifications"
    )
    standard = models.ForeignKey(Standard, on_delete=models.PROTECT, related_name="certifications")
    farmer = models.ForeignKey(
        "organizations.Farmer",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="certifications",
    )
    farm = models.ForeignKey(
        "farms.Farm",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="certifications",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PREPARING)
    certificate_number = models.CharField(max_length=80, blank=True)
    issued_on = models.DateField(null=True, blank=True)
    expires_on = models.DateField(null=True, blank=True)
    decision_notes = models.TextField(blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="certification_decisions",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["organization", "status"])]

    def __str__(self) -> str:
        return f"{self.standard.code} ({self.status})"


class ComplianceItem(UUIDModel):
    class State(models.TextChoices):
        MISSING = "missing", "Missing"
        DECLARED = "declared", "Farmer declared"
        EVIDENCE = "evidence_attached", "Evidence attached"
        VERIFIED = "verified", "Verified"
        NOT_APPLICABLE = "not_applicable", "Not applicable"

    certification = models.ForeignKey(
        Certification, on_delete=models.CASCADE, related_name="items"
    )
    requirement = models.ForeignKey(Requirement, on_delete=models.PROTECT, related_name="items")
    state = models.CharField(max_length=24, choices=State.choices, default=State.MISSING)
    note = models.TextField(blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="compliance_updates",
    )

    class Meta:
        ordering = ["requirement__code"]
        constraints = [
            models.UniqueConstraint(
                fields=["certification", "requirement"],
                name="uniq_compliance_item",
            )
        ]

    def __str__(self) -> str:
        return f"{self.requirement.code} {self.state}"


class Evidence(UUIDModel):
    class Kind(models.TextChoices):
        DOCUMENT = "document", "Document"
        DECLARATION = "declaration", "Declaration"
        PHOTO = "photo", "Photo"
        INSPECTION = "inspection", "Inspection"

    item = models.ForeignKey(ComplianceItem, on_delete=models.CASCADE, related_name="evidence")
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.DOCUMENT)
    note = models.TextField(blank=True)
    file = models.FileField(upload_to=evidence_upload, null=True, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="compliance_evidence",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.kind} for {self.item_id}"


class CorrectiveAction(UUIDModel):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        COMPLETED = "completed", "Completed"

    certification = models.ForeignKey(
        Certification, on_delete=models.CASCADE, related_name="actions"
    )
    item = models.ForeignKey(
        ComplianceItem,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="actions",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    due_on = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    completed_on = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["status", "due_on"]

    def __str__(self) -> str:
        return self.title


class Reminder(UUIDModel):
    class Kind(models.TextChoices):
        EXPIRY = "expiry", "Expiry"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="reminders"
    )
    certification = models.ForeignKey(
        Certification, on_delete=models.CASCADE, related_name="reminders"
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    due_on = models.DateField()
    message = models.CharField(max_length=240)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["certification", "kind", "due_on"],
                name="uniq_certification_reminder",
            )
        ]
        ordering = ["due_on"]

    def __str__(self) -> str:
        return self.message
