from rest_framework import serializers

from api.access import OrgViewSet
from api.checks import farm_in_scope
from api.roles import FARM_WRITE, OPERATIONS
from crops.models import Crop, Planting


class CropSerializer(serializers.ModelSerializer):
    class Meta:
        model = Crop
        fields = ["id", "name", "variety", "created_at"]
        read_only_fields = ["id", "created_at"]


class PlantingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Planting
        fields = [
            "id",
            "field",
            "crop",
            "season_year",
            "planted_on",
            "expected_harvest_on",
            "area_hectares",
            "status",
            "notes",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs):
        field = attrs.get("field") or getattr(self.instance, "field", None)
        crop = attrs.get("crop") or getattr(self.instance, "crop", None)
        farm_in_scope(self.context, field.farm)
        member = self.context["membership"]
        if crop.organization_id != member.organization_id:
            raise serializers.ValidationError({"crop": "Crop was not found in your organization."})
        return attrs


class CropViewSet(OrgViewSet):
    queryset = Crop.objects.all()
    serializer_class = CropSerializer
    write_roles = FARM_WRITE
    search_fields = ("name", "variety")


class PlantingViewSet(OrgViewSet):
    queryset = Planting.objects.select_related("field__farm", "crop")
    serializer_class = PlantingSerializer
    write_roles = OPERATIONS
    org_field = None
    org_lookup = "field__farm__organization"
    farmer_lookup = "field__farm__farmer__user"
