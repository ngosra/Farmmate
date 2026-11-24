from rest_framework import serializers

from organizations.models import Membership


def farm_in_scope(context, farm):
    membership = context["membership"]
    if farm is None or farm.organization_id != membership.organization_id:
        raise serializers.ValidationError("Farm was not found in your organization.")
    user = context["request"].user
    if membership.role == Membership.Role.FARMER and not user.is_superuser:
        if farm.farmer.user_id != user.id:
            raise serializers.ValidationError("You can only use your own farms.")
    return farm


def positive(value, label="Quantity"):
    if value is None or value <= 0:
        raise serializers.ValidationError(f"{label} must be greater than zero.")
    return value
