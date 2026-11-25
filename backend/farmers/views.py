from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from api.access import OrgViewSet, allow
from api.audit import record
from api.files import validate_upload
from api.roles import FARMER_RECORDS, OPERATIONS
from farmers.models import FarmerDeclaration, Identification
from organizations.models import Farmer, Membership
from organizations.services import create_member


class FarmerSerializer(serializers.ModelSerializer):
    def validate_farmer_id(self, value):
        return value.strip().upper()

    class Meta:
        model = Farmer
        fields = [
            "id",
            "farmer_id",
            "display_name",
            "phone",
            "email",
            "national_id",
            "region",
            "community",
            "date_of_birth",
            "notes",
            "user",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]


class DeclarationSerializer(serializers.ModelSerializer):
    class Meta:
        model = FarmerDeclaration
        fields = ["id", "farmer", "title", "statement", "declared_on", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_farmer(self, farmer):
        member = self.context["membership"]
        if farmer.organization_id != member.organization_id:
            raise serializers.ValidationError("Farmer was not found in your organization.")
        if (
            member.role == Membership.Role.FARMER
            and farmer.user_id != self.context["request"].user.id
        ):
            raise serializers.ValidationError("You can only declare for your own profile.")
        return farmer


class IdentificationSerializer(serializers.ModelSerializer):
    file = serializers.FileField(required=False, allow_null=True, validators=[validate_upload])

    class Meta:
        model = Identification
        fields = ["id", "farmer", "kind", "number", "file", "notes", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_farmer(self, farmer):
        member = self.context["membership"]
        if farmer.organization_id != member.organization_id:
            raise serializers.ValidationError("Farmer was not found in your organization.")
        if (
            member.role == Membership.Role.FARMER
            and farmer.user_id != self.context["request"].user.id
        ):
            raise serializers.ValidationError("You can only update your own identification.")
        return farmer


class FarmerViewSet(OrgViewSet):
    queryset = Farmer.objects.all()
    serializer_class = FarmerSerializer
    write_roles = FARMER_RECORDS
    farmer_lookup = "user"
    search_fields = ("display_name", "farmer_id", "community", "region")

    def create(self, request, *args, **kwargs):
        member = allow(request, self.write_roles)
        payload = request.data.copy()
        create_login = str(payload.pop("create_login", "")).lower() in {"1", "true", "yes"}
        if hasattr(payload, "get"):
            create_login = create_login or str(request.data.get("create_login", "")).lower() in {
                "1",
                "true",
                "yes",
            }
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if Farmer.objects.filter(organization=member.organization,
            farmer_id=data["farmer_id"]).exists():
            raise ValidationError(
                {"farmer_id": "This FarmerID is already used in the organization."}
            )
        with transaction.atomic():
            if create_login:
                membership = create_member(
                    member.organization,
                    {
                        "email": data.get("email") or request.data.get("login_email"),
                        "password": request.data.get("password", ""),
                        "role": Membership.Role.FARMER,
                        "first_name": request.data.get("first_name", ""),
                        "last_name": request.data.get("last_name", ""),
                        "phone": data.get("phone", ""),
                        "farmer_id": data["farmer_id"],
                        "display_name": data["display_name"],
                    },
                )
                farmer = membership.user.farmer_profiles.get(organization=member.organization)
                for field in (
                    "national_id",
                    "region",
                    "community",
                    "date_of_birth",
                    "notes",
                ):
                    if data.get(field):
                        setattr(farmer, field, data[field])
                farmer.save()
            else:
                farmer = serializer.save(organization=member.organization)
        record(request, "create", farmer, f"Registered farmer {farmer.display_name}")
        return Response(self.get_serializer(farmer).data, status=201)


class DeclarationViewSet(OrgViewSet):
    queryset = FarmerDeclaration.objects.select_related("farmer")
    serializer_class = DeclarationSerializer
    write_roles = OPERATIONS
    org_field = None
    org_lookup = "farmer__organization"
    farmer_lookup = "farmer__user"
    stamp_user = "created_by"


class IdentificationViewSet(OrgViewSet):
    queryset = Identification.objects.select_related("farmer")
    serializer_class = IdentificationSerializer
    write_roles = OPERATIONS
    org_field = None
    org_lookup = "farmer__organization"
    farmer_lookup = "farmer__user"
