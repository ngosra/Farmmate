from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from api.access import OrgViewSet, allow
from api.audit import record
from api.roles import ADMIN
from organizations.models import Membership
from organizations.scoping import organizations_for
from organizations.serializers import OrganizationSerializer
from organizations.services import create_member


class OrganizationListView(ListAPIView):
    serializer_class = OrganizationSerializer

    def get_queryset(self):
        return organizations_for(self.request.user).order_by("name")


class OrganizationDetailView(RetrieveAPIView):
    serializer_class = OrganizationSerializer

    def get_queryset(self):
        return organizations_for(self.request.user)


class MemberSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    phone = serializers.CharField(source="user.phone", read_only=True)
    farmer_id = serializers.CharField(source="user.farmer_id", read_only=True)
    is_active = serializers.BooleanField(source="user.is_active", read_only=True)

    class Meta:
        model = Membership
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "phone",
            "farmer_id",
            "role",
            "is_active",
            "created_at",
        ]


class MemberWriteSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=Membership.Role.choices)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    farmer_id = serializers.CharField(required=False, allow_blank=True)
    display_name = serializers.CharField(required=False, allow_blank=True)


class MemberUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=Membership.Role.choices, required=False)
    is_active = serializers.BooleanField(required=False)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)


class MemberViewSet(OrgViewSet):
    queryset = Membership.objects.select_related("user")
    serializer_class = MemberSerializer
    write_roles = ADMIN
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        member = allow(self.request, ADMIN)
        return super().get_queryset().filter(organization=member.organization)

    def create(self, request, *args, **kwargs):
        member = allow(request, ADMIN)
        serializer = MemberWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership = create_member(member.organization, serializer.validated_data)
        record(request, "create", membership, f"Added {membership.user.email} as {membership.role}")
        return Response(MemberSerializer(membership).data, status=201)

    def partial_update(self, request, *args, **kwargs):
        actor = allow(request, ADMIN)
        membership = self.get_object()
        serializer = MemberUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        new_role = data.get("role", membership.role)
        if membership.role == Membership.Role.ORG_ADMIN and new_role != Membership.Role.ORG_ADMIN:
            others = Membership.objects.filter(
                organization=actor.organization,
                role=Membership.Role.ORG_ADMIN,
            ).exclude(pk=membership.pk)
            if not others.exists():
                raise ValidationError(
                    {"role": "The organization needs at least one administrator."}
                )
        if data.get("is_active") is False and membership.user_id == request.user.id:
            raise ValidationError({"is_active": "You cannot deactivate your own account."})
        membership.role = new_role
        membership.save(update_fields=["role"])
        user = membership.user
        for field in ("first_name", "last_name", "phone"):
            if field in data:
                setattr(user, field, data[field])
        if "is_active" in data:
            user.is_active = data["is_active"]
        user.save()
        record(request, "update", membership, f"Updated account {user.email}")
        return Response(MemberSerializer(membership).data)


class AuditLogView(APIView):
    def get(self, request):
        member = allow(request, ADMIN)
        from organizations.models import AuditLog

        rows = AuditLog.objects.filter(organization=member.organization).select_related("actor")
        rows = rows[:100]
        return Response(
            [
                {
                    "id": str(row.id),
                    "action": row.action,
                    "entity_type": row.entity_type,
                    "entity_id": row.entity_id,
                    "summary": row.summary,
                    "actor": row.actor.email if row.actor_id else None,
                    "created_at": row.created_at,
                }
                for row in rows
            ]
        )


# Imported for the permission error type used by callers that catch it.
_ = PermissionDenied
