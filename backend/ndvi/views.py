from rest_framework import serializers

from api.access import OrgViewSet
from api.checks import farm_in_scope
from api.roles import OPERATIONS
from ndvi.models import Observation


class ObservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Observation
        fields = [
            "id",
            "field",
            "observed_on",
            "ndvi_mean",
            "source",
            "provider",
            "notes",
            "created_at",
        ]
        read_only_fields = ["id", "source", "provider", "created_at"]

    def validate_field(self, field):
        farm_in_scope(self.context, field.farm)
        return field

    def validate_ndvi_mean(self, value):
        if value < -1 or value > 1:
            raise serializers.ValidationError("NDVI must be between -1 and 1.")
        return value


class ObservationViewSet(OrgViewSet):
    queryset = Observation.objects.select_related("field__farm")
    serializer_class = ObservationSerializer
    write_roles = OPERATIONS
    org_field = None
    org_lookup = "field__farm__organization"
    farmer_lookup = "field__farm__farmer__user"

    def perform_create(self, serializer):
        from api.access import allow
        from api.audit import record

        allow(self.request, OPERATIONS)
        instance = serializer.save(
            source=Observation.Source.MANUAL,
            provider="",
            recorded_by=self.request.user,
        )
        record(self.request, "create", instance, f"Manual NDVI for {instance.field.name}")
        return instance
