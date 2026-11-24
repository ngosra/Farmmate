from rest_framework import serializers

from api.access import OrgViewSet
from api.checks import farm_in_scope, positive
from api.roles import OPERATIONS
from production.models import Activity, Harvest, StorageRecord


class ActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = [
            "id",
            "farm",
            "field",
            "farmer",
            "kind",
            "occurred_on",
            "notes",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs):
        farm = attrs.get("farm") or getattr(self.instance, "farm", None)
        field = attrs.get("field", getattr(self.instance, "field", None))
        farmer = attrs.get("farmer", getattr(self.instance, "farmer", None))
        farm_in_scope(self.context, farm)
        if field and field.farm_id != farm.id:
            raise serializers.ValidationError({"field": "Field does not belong to that farm."})
        member = self.context["membership"]
        if farmer and farmer.organization_id != member.organization_id:
            raise serializers.ValidationError(
                {"farmer": "Farmer was not found in your organization."}
            )
        return attrs


class HarvestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Harvest
        fields = [
            "id",
            "farm",
            "field",
            "planting",
            "crop",
            "harvested_on",
            "quantity_kg",
            "quality",
            "storage_location",
            "notes",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_quantity_kg(self, value):
        return positive(value, "Harvest quantity")

    def validate(self, attrs):
        farm = attrs.get("farm") or getattr(self.instance, "farm", None)
        field = attrs.get("field") or getattr(self.instance, "field", None)
        farm_in_scope(self.context, farm)
        if field.farm_id != farm.id:
            raise serializers.ValidationError({"field": "Field does not belong to that farm."})
        crop = attrs.get("crop", getattr(self.instance, "crop", None))
        planting = attrs.get("planting", getattr(self.instance, "planting", None))
        member = self.context["membership"]
        if crop and crop.organization_id != member.organization_id:
            raise serializers.ValidationError({"crop": "Crop was not found in your organization."})
        if planting and planting.field_id != field.id:
            raise serializers.ValidationError(
                {"planting": "Planting does not belong to that field."}
            )
        return attrs


class StorageSerializer(serializers.ModelSerializer):
    class Meta:
        model = StorageRecord
        fields = ["id", "harvest", "location", "quantity_kg", "stored_on", "notes", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_quantity_kg(self, value):
        return positive(value, "Stored quantity")

    def validate(self, attrs):
        from organizations.models import Membership

        harvest = attrs.get("harvest", getattr(self.instance, "harvest", None))
        member = self.context["membership"]
        if harvest is None:
            user = self.context["request"].user
            if member.role == Membership.Role.FARMER and not user.is_superuser:
                raise serializers.ValidationError({"harvest": "Choose one of your harvests."})
            return attrs
        farm_in_scope(self.context, harvest.farm)
        return attrs


class ActivityViewSet(OrgViewSet):
    queryset = Activity.objects.select_related("farm", "field", "farmer")
    serializer_class = ActivitySerializer
    write_roles = OPERATIONS
    farmer_lookup = "farm__farmer__user"
    stamp_user = "actor"


class HarvestViewSet(OrgViewSet):
    queryset = Harvest.objects.select_related("farm", "field", "crop")
    serializer_class = HarvestSerializer
    write_roles = OPERATIONS
    farmer_lookup = "farm__farmer__user"
    stamp_user = "recorded_by"


class StorageViewSet(OrgViewSet):
    queryset = StorageRecord.objects.select_related("harvest__farm")
    serializer_class = StorageSerializer
    write_roles = OPERATIONS
    farmer_lookup = "harvest__farm__farmer__user"
