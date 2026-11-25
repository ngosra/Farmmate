from django.db.models import Count, Sum
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response

from api.access import OrgViewSet, allow
from api.audit import record
from api.checks import farm_in_scope
from api.files import validate_upload
from api.roles import FARM_WRITE, NDVI, OPERATIONS
from farms.geo import hectares_from_polygon, polygon_to_geojson
from farms.land import missing_land_use_years
from farms.models import Farm, FarmDocument, Field, LandUse
from ndvi.models import Observation
from ndvi.providers import SatelliteError, get_provider


class BoundaryField(serializers.Field):
    def to_representation(self, value):
        return polygon_to_geojson(value)

    def to_internal_value(self, data):
        if data in (None, ""):
            return None
        from farms.geo import polygon_from_geojson

        return polygon_from_geojson(data)


class FarmSerializer(serializers.ModelSerializer):
    code = serializers.CharField(required=False, allow_blank=True)
    field_count = serializers.IntegerField(read_only=True)
    mapped_hectares = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True, allow_null=True
    )

    class Meta:
        model = Farm
        fields = [
            "id",
            "farmer",
            "name",
            "code",
            "latitude",
            "longitude",
            "country",
            "region",
            "district",
            "community",
            "area_hectares",
            "mapped_hectares",
            "established_year",
            "status",
            "notes",
            "field_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "field_count", "mapped_hectares"]
        validators = []

    def validate(self, attrs):
        lat = attrs.get("latitude", getattr(self.instance, "latitude", None))
        lon = attrs.get("longitude", getattr(self.instance, "longitude", None))
        if (lat is None) != (lon is None):
            raise serializers.ValidationError(
                "Enter both latitude and longitude, or leave both empty."
            )
        if lat is not None and not (-90 <= float(lat) <= 90):
            raise serializers.ValidationError({"latitude": "Latitude must be between -90 and 90."})
        if lon is not None and not (-180 <= float(lon) <= 180):
            raise serializers.ValidationError(
                {"longitude": "Longitude must be between -180 and 180."}
            )
        farmer = attrs.get("farmer") or getattr(self.instance, "farmer", None)
        member = self.context["membership"]
        if farmer is None or farmer.organization_id != member.organization_id:
            raise serializers.ValidationError(
                {"farmer": "Farmer was not found in your organization."}
            )
        code = (attrs.get("code") or "").strip()
        if code:
            existing = Farm.objects.filter(organization=member.organization, code=code.upper())
            if self.instance is not None:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise serializers.ValidationError({"code": "A farm with this code already exists."})
        return attrs

    def create(self, validated_data):
        if not validated_data.get("code"):
            count = Farm.objects.filter(organization=validated_data["organization"]).count() + 1
            validated_data["code"] = f"FARM-{count:03d}"
        else:
            validated_data["code"] = validated_data["code"].strip().upper()
        return super().create(validated_data)


class FieldSerializer(serializers.ModelSerializer):
    code = serializers.CharField(required=False, allow_blank=True)
    boundary = BoundaryField(required=False, allow_null=True)
    missing_land_use_years = serializers.SerializerMethodField()

    class Meta:
        model = Field
        fields = [
            "id",
            "farm",
            "name",
            "code",
            "boundary",
            "area_hectares",
            "soil_notes",
            "missing_land_use_years",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "missing_land_use_years"]
        validators = []

    def get_missing_land_use_years(self, obj):
        return missing_land_use_years(obj)

    def validate_farm(self, farm):
        return farm_in_scope(self.context, farm)

    def validate(self, attrs):
        boundary = attrs.get("boundary", serializers.empty)
        if (
            boundary is not serializers.empty
            and boundary is not None
            and "area_hectares" not in attrs
        ):
            attrs["area_hectares"] = hectares_from_polygon(boundary)
        if boundary is not serializers.empty and boundary is None and "area_hectares" not in attrs:
            attrs["area_hectares"] = None
        farm = attrs.get("farm") or getattr(self.instance, "farm", None)
        code = (attrs.get("code") or "").strip()
        if farm and code:
            existing = Field.objects.filter(farm=farm, code=code.upper())
            if self.instance is not None:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise serializers.ValidationError(
                    {"code": "A field with this code already exists."}
                )
        return attrs

    def create(self, validated_data):
        if not validated_data.get("code"):
            count = Field.objects.filter(farm=validated_data["farm"]).count() + 1
            validated_data["code"] = f"FLD-{count:03d}"
        else:
            validated_data["code"] = validated_data["code"].strip().upper()
        return super().create(validated_data)


class LandUseSerializer(serializers.ModelSerializer):
    class Meta:
        model = LandUse
        fields = ["id", "field", "year", "use", "notes", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_field(self, field):
        farm_in_scope(self.context, field.farm)
        return field

    def validate_year(self, year):
        if year < 1900 or year > 2200:
            raise serializers.ValidationError("Year is out of range.")
        return year


class FarmDocumentSerializer(serializers.ModelSerializer):
    file = serializers.FileField(validators=[validate_upload])

    class Meta:
        model = FarmDocument
        fields = ["id", "farm", "title", "file", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_farm(self, farm):
        return farm_in_scope(self.context, farm)


class FarmViewSet(OrgViewSet):
    serializer_class = FarmSerializer
    write_roles = FARM_WRITE
    farmer_lookup = "farmer__user"
    search_fields = ("name", "code", "community", "region")

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("farmer")
            .annotate(field_count=Count("fields"), mapped_hectares=Sum("fields__area_hectares"))
            .order_by("name")
        )

    queryset = Farm.objects.all()


class FieldViewSet(OrgViewSet):
    queryset = Field.objects.select_related("farm")
    serializer_class = FieldSerializer
    write_roles = OPERATIONS
    org_field = None
    org_lookup = "farm__organization"
    farmer_lookup = "farm__farmer__user"
    search_fields = ("name", "code", "farm__name")

    @action(detail=True, methods=["post"], url_path="satellite-refresh")
    def satellite_refresh(self, request, pk=None):
        field = self.get_object()
        allow(request, NDVI)
        provider = get_provider()
        if not provider.configured():
            return Response({"detail": provider.reason, "stored": 0}, status=503)
        try:
            rows = provider.fetch(field)
        except SatelliteError as exc:
            return Response({"detail": str(exc), "stored": 0}, status=502)
        stored = 0
        for row in rows:
            Observation.objects.create(
                field=field,
                observed_on=row["observed_on"],
                ndvi_mean=row["ndvi_mean"],
                source=Observation.Source.SATELLITE,
                provider=provider.code,
                external_id=row.get("external_id", ""),
                notes=row.get("notes", ""),
            )
            stored += 1
        record(request, "update", field, f"Stored {stored} satellite observations")
        return Response({"stored": stored})


class LandUseViewSet(OrgViewSet):
    queryset = LandUse.objects.select_related("field__farm")
    serializer_class = LandUseSerializer
    write_roles = OPERATIONS
    org_field = None
    org_lookup = "field__farm__organization"
    farmer_lookup = "field__farm__farmer__user"


class FarmDocumentViewSet(OrgViewSet):
    queryset = FarmDocument.objects.select_related("farm")
    serializer_class = FarmDocumentSerializer
    write_roles = OPERATIONS
    org_field = None
    org_lookup = "farm__organization"
    farmer_lookup = "farm__farmer__user"
    stamp_user = "uploaded_by"
