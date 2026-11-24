from django.db import transaction
from rest_framework import serializers
from rest_framework.response import Response

from api.access import OrgViewSet, allow
from api.audit import record
from api.checks import farm_in_scope
from api.roles import INSPECT
from certification.models import Certification
from inspections.models import Inspection, InspectionCheck


class InspectionCheckSerializer(serializers.ModelSerializer):
    class Meta:
        model = InspectionCheck
        fields = ["id", "prompt", "requirement", "result", "notes"]
        read_only_fields = ["id", "prompt", "requirement"]


class InspectionSerializer(serializers.ModelSerializer):
    checks = InspectionCheckSerializer(many=True, read_only=True)
    farm_name = serializers.CharField(source="farm.name", read_only=True)

    class Meta:
        model = Inspection
        fields = [
            "id",
            "farm",
            "farm_name",
            "certification",
            "inspector",
            "scheduled_for",
            "completed_on",
            "status",
            "summary",
            "checks",
            "created_at",
        ]
        read_only_fields = ["id", "inspector", "created_at", "checks", "farm_name"]


class InspectionWriteSerializer(serializers.Serializer):
    farm = serializers.UUIDField()
    certification = serializers.UUIDField(required=False, allow_null=True)
    scheduled_for = serializers.DateTimeField()
    summary = serializers.CharField(required=False, allow_blank=True)
    checks = serializers.ListField(child=serializers.CharField(max_length=240), required=False)


class InspectionViewSet(OrgViewSet):
    queryset = Inspection.objects.select_related("farm").prefetch_related("checks")
    serializer_class = InspectionSerializer
    write_roles = INSPECT
    farmer_lookup = "farm__farmer__user"

    def create(self, request, *args, **kwargs):
        from farms.models import Farm

        member = allow(request, INSPECT)
        serializer = InspectionWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        farm = Farm.objects.filter(pk=data["farm"], organization=member.organization).first()
        farm = farm_in_scope({**self.get_serializer_context(), "membership": member}, farm)
        certification = None
        if data.get("certification"):
            certification = Certification.objects.filter(
                pk=data["certification"], organization=member.organization
            ).first()
            if certification is None:
                raise serializers.ValidationError(
                    {"certification": "Certification was not found in your organization."}
                )
        with transaction.atomic():
            inspection = Inspection.objects.create(
                organization=member.organization,
                farm=farm,
                certification=certification,
                inspector=request.user,
                scheduled_for=data["scheduled_for"],
                summary=data.get("summary", ""),
            )
            prompts = [{"prompt": prompt, "requirement": None} for prompt in
                data.get("checks") or []]
            if not prompts and certification is not None:
                prompts = [
                    {"prompt": item.requirement.title, "requirement": item.requirement}
                    for item in certification.items.select_related("requirement")
                ]
            if not prompts:
                prompts = [{"prompt": "General farm walk-through", "requirement": None}]
            for prompt in prompts:
                InspectionCheck.objects.create(
                    inspection=inspection,
                    prompt=prompt["prompt"],
                    requirement=prompt["requirement"],
                )
        record(request, "create", inspection, f"Scheduled inspection for {farm.name}")
        return Response(InspectionSerializer(inspection).data, status=201)


class InspectionCheckViewSet(OrgViewSet):
    queryset = InspectionCheck.objects.select_related("inspection__farm")
    serializer_class = InspectionCheckSerializer
    write_roles = INSPECT
    org_field = None
    org_lookup = "inspection__organization"
    farmer_lookup = "inspection__farm__farmer__user"
    http_method_names = ["get", "patch", "head", "options"]
