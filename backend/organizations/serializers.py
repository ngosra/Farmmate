from rest_framework import serializers

from organizations.models import Organization


class OrganizationSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = ["id", "name", "slug", "role"]

    def get_role(self, obj: Organization) -> str | None:
        request = self.context.get("request")
        if request is None or not request.user.is_authenticated:
            return None
        membership = obj.memberships.filter(user=request.user).first()
        return membership.role if membership else None
