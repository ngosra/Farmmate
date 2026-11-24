from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from api.access import OrgViewSet, allow, require_membership
from api.audit import record
from api.files import validate_upload
from api.roles import ADMIN, CERT_DECIDE, OPERATIONS
from certification.models import (
    Certification,
    ComplianceItem,
    CorrectiveAction,
    Evidence,
    Requirement,
    Standard,
)
from certification.services import (
    open_certification,
    readiness,
    set_decision,
    set_item_state,
    visible_certifications,
)


class RequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Requirement
        fields = ["id", "code", "title", "description", "weight"]


class StandardSerializer(serializers.ModelSerializer):
    requirements = RequirementSerializer(many=True, read_only=True)

    class Meta:
        model = Standard
        fields = ["id", "code", "name", "authority", "summary", "organization", "requirements"]
        read_only_fields = fields


class StandardWriteSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=40)
    name = serializers.CharField(max_length=160)
    authority = serializers.CharField(required=False, allow_blank=True)
    summary = serializers.CharField(required=False, allow_blank=True)
    requirements = serializers.ListField(child=serializers.DictField(), allow_empty=False)


class EvidenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Evidence
        fields = ["id", "kind", "note", "file", "created_at"]
        read_only_fields = fields


class ComplianceItemSerializer(serializers.ModelSerializer):
    requirement = RequirementSerializer(read_only=True)
    evidence = EvidenceSerializer(many=True, read_only=True)

    class Meta:
        model = ComplianceItem
        fields = ["id", "certification", "requirement", "state", "note", "evidence", "updated_at"]
        read_only_fields = fields


class CertificationSerializer(serializers.ModelSerializer):
    standard = StandardSerializer(read_only=True)
    readiness = serializers.SerializerMethodField()
    items = ComplianceItemSerializer(many=True, read_only=True)

    class Meta:
        model = Certification
        fields = [
            "id",
            "standard",
            "farmer",
            "farm",
            "status",
            "certificate_number",
            "issued_on",
            "expires_on",
            "decision_notes",
            "readiness",
            "items",
            "created_at",
        ]
        read_only_fields = fields

    def get_readiness(self, obj):
        return readiness(obj)


class CertificationListSerializer(serializers.ModelSerializer):
    standard_code = serializers.CharField(source="standard.code", read_only=True)
    readiness = serializers.SerializerMethodField()

    class Meta:
        model = Certification
        fields = [
            "id",
            "standard",
            "standard_code",
            "farmer",
            "farm",
            "status",
            "certificate_number",
            "expires_on",
            "readiness",
            "created_at",
        ]

    def get_readiness(self, obj):
        return readiness(obj)


class CertificationOpenSerializer(serializers.Serializer):
    standard_id = serializers.UUIDField()
    farmer = serializers.UUIDField(required=False, allow_null=True)
    farm = serializers.UUIDField(required=False, allow_null=True)


class DecisionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Certification.Status.choices)
    certificate_number = serializers.CharField(required=False, allow_blank=True)
    issued_on = serializers.DateField(required=False, allow_null=True)
    expires_on = serializers.DateField(required=False, allow_null=True)
    decision_notes = serializers.CharField(required=False, allow_blank=True)


class CorrectiveActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CorrectiveAction
        fields = [
            "id",
            "certification",
            "item",
            "title",
            "description",
            "due_on",
            "status",
            "completed_on",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs):
        member = self.context["membership"]
        certification = attrs.get("certification") or getattr(self.instance, "certification", None)
        if certification.organization_id != member.organization_id:
            raise serializers.ValidationError(
                {"certification": "Certification was not found in your organization."}
            )
        item = attrs.get("item", getattr(self.instance, "item", None))
        if item and item.certification_id != certification.id:
            raise serializers.ValidationError(
                {"item": "That checklist item belongs to another case."}
            )
        if attrs.get("status") == CorrectiveAction.Status.COMPLETED and not attrs.get(
            "completed_on"
        ):
            attrs["completed_on"] = timezone.localdate()
        return attrs


class StandardViewSet(OrgViewSet):
    queryset = Standard.objects.prefetch_related("requirements")
    serializer_class = StandardSerializer
    write_roles = ADMIN
    org_field = None
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        member = self.get_membership()
        return Standard.objects.filter(
            Q(organization__isnull=True) | Q(organization=member.organization)
        ).prefetch_related("requirements")

    def create(self, request, *args, **kwargs):
        member = allow(request, ADMIN)
        serializer = StandardWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        code = data["code"].strip().upper().replace(" ", "_")
        if Standard.objects.filter(code=code).exists():
            raise ValidationError({"code": "A standard with this code already exists."})
        with transaction.atomic():
            standard = Standard.objects.create(
                organization=member.organization,
                code=code,
                name=data["name"].strip(),
                authority=data.get("authority", ""),
                summary=data.get("summary", ""),
            )
            for row in data["requirements"]:
                title = str(row.get("title") or "").strip()
                requirement_code = str(row.get("code") or "").strip().upper().replace(" ", "_")
                if not title or not requirement_code:
                    raise ValidationError(
                        {"requirements": "Each requirement needs a code and a title."}
                    )
                weight = int(row.get("weight") or 1)
                if weight < 1:
                    raise ValidationError({"requirements": "Weight must be at least 1."})
                Requirement.objects.create(
                    standard=standard,
                    code=requirement_code,
                    title=title,
                    description=str(row.get("description") or ""),
                    weight=weight,
                )
        record(request, "create", standard, f"Added standard {standard.code}")
        return Response(StandardSerializer(standard).data, status=201)


class CertificationViewSet(OrgViewSet):
    queryset = Certification.objects.select_related("standard", "farmer", "farm").prefetch_related(
        "items__requirement", "items__evidence"
    )
    write_roles = OPERATIONS
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        return visible_certifications(self.request.user, self.get_membership()).select_related(
            "standard", "farmer", "farm"
        ).prefetch_related("items__requirement", "items__evidence")

    def get_serializer_class(self):
        if self.action == "list":
            return CertificationListSerializer
        return CertificationSerializer

    def create(self, request, *args, **kwargs):
        from farms.models import Farm
        from organizations.models import Farmer, Membership

        member = allow(request, OPERATIONS)
        serializer = CertificationOpenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        standard = Standard.objects.filter(pk=data["standard_id"]).first()
        if standard is None:
            raise ValidationError({"standard_id": "Standard was not found."})
        farmer = None
        farm = None
        if member.role == Membership.Role.FARMER and not request.user.is_superuser:
            farmer = Farmer.objects.filter(organization=member.organization,
                user=request.user).first()
            if farmer is None:
                raise ValidationError({"farmer": "Your user is not linked to a farmer profile."})
        elif data.get("farmer"):
            farmer = Farmer.objects.filter(
                organization=member.organization, pk=data["farmer"]
            ).first()
            if farmer is None:
                raise ValidationError({"farmer": "Farmer was not found in your organization."})
        if data.get("farm"):
            farm = Farm.objects.filter(organization=member.organization, pk=data["farm"]).first()
            if farm is None:
                raise ValidationError({"farm": "Farm was not found in your organization."})
        certification = open_certification(
            organization=member.organization,
            standard=standard,
            actor=request.user,
            farmer=farmer,
            farm=farm,
        )
        record(request, "create", certification, f"Opened {certification.standard.code}")
        return Response(CertificationSerializer(certification).data, status=201)

    def perform_destroy(self, instance):
        allow(self.request, ADMIN)
        if instance.status == Certification.Status.CERTIFIED:
            raise ValidationError({"detail": "An official certification cannot be deleted."})
        record(self.request, "delete", instance, f"Deleted {instance}")
        instance.delete()

    @action(detail=True, methods=["post"])
    def decision(self, request, pk=None):
        certification = self.get_object()
        member = require_membership(request)
        serializer = DecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        set_decision(
            certification,
            status=serializer.validated_data["status"],
            actor=request.user,
            membership=member,
            certificate_number=serializer.validated_data.get("certificate_number", ""),
            issued_on=serializer.validated_data.get("issued_on"),
            expires_on=serializer.validated_data.get("expires_on"),
            decision_notes=serializer.validated_data.get("decision_notes", ""),
        )
        record(request, "update", certification, f"Set status to {certification.status}")
        return Response(CertificationSerializer(certification).data)


class ComplianceItemViewSet(OrgViewSet):
    serializer_class = ComplianceItemSerializer
    queryset = ComplianceItem.objects.select_related("requirement",
        "certification").prefetch_related(
        "evidence"
    )
    http_method_names = ["get", "patch", "post", "head", "options"]
    org_field = None

    def get_queryset(self):
        visible = visible_certifications(self.request.user, self.get_membership())
        return self.queryset.filter(certification__in=visible)

    def partial_update(self, request, *args, **kwargs):
        item = self.get_object()
        member = require_membership(request)
        state = request.data.get("state", item.state)
        note = request.data.get("note", item.note)
        set_item_state(item, state=state, actor=request.user, membership=member, note=note)
        record(request, "update", item, f"Set {item.requirement.code} to {item.state}")
        return Response(self.get_serializer(item).data)

    @action(detail=True, methods=["post"])
    def evidence(self, request, pk=None):
        item = self.get_object()
        member = require_membership(request)
        upload = request.FILES.get("file")
        if upload is not None:
            validate_upload(upload)
        note = request.data.get("note", "")
        if not upload and not note:
            raise ValidationError({"detail": "Add a file or a note."})
        row = Evidence.objects.create(
            item=item,
            kind=request.data.get("kind") or Evidence.Kind.DOCUMENT,
            note=note,
            file=upload,
            uploaded_by=request.user,
        )
        if item.state in {ComplianceItem.State.MISSING, ComplianceItem.State.DECLARED}:
            set_item_state(
                item,
                state=ComplianceItem.State.EVIDENCE,
                actor=request.user,
                membership=member,
                note=item.note,
            )
        record(request, "create", row, f"Added evidence to {item.requirement.code}")
        return Response(ComplianceItemSerializer(item, context={"request": request}).data,
            status=201)


class CorrectiveActionViewSet(OrgViewSet):
    queryset = CorrectiveAction.objects.select_related("certification")
    serializer_class = CorrectiveActionSerializer
    write_roles = OPERATIONS | CERT_DECIDE
    org_field = None
    org_lookup = "certification__organization"
