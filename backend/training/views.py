from rest_framework import serializers

from api.access import OrgViewSet
from api.files import validate_upload
from api.roles import OPERATIONS, TRAIN
from training.models import Attendance, TrainingMaterial, TrainingSession


class TrainingMaterialSerializer(serializers.ModelSerializer):
    file = serializers.FileField(required=False, allow_null=True, validators=[validate_upload])

    class Meta:
        model = TrainingMaterial
        fields = ["id", "session", "title", "link", "file", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_session(self, session):
        member = self.context["membership"]
        if session.organization_id != member.organization_id:
            raise serializers.ValidationError("Training session was not found.")
        return session

    def validate(self, attrs):
        if not attrs.get("link") and not attrs.get("file") and self.instance is None:
            if not (self.initial_data.get("link") or self.initial_data.get("file")):
                raise serializers.ValidationError("Add a file or a link.")
        return attrs


class AttendanceSerializer(serializers.ModelSerializer):
    farmer_name = serializers.CharField(source="farmer.display_name", read_only=True)

    class Meta:
        model = Attendance
        fields = ["id", "session", "farmer", "farmer_name", "present", "created_at"]
        read_only_fields = ["id", "created_at", "farmer_name"]

    def validate(self, attrs):
        member = self.context["membership"]
        session = attrs.get("session") or getattr(self.instance, "session", None)
        farmer = attrs.get("farmer") or getattr(self.instance, "farmer", None)
        if session.organization_id != member.organization_id:
            raise serializers.ValidationError({"session": "Training session was not found."})
        if farmer.organization_id != member.organization_id:
            raise serializers.ValidationError({"farmer": "Farmer was not found."})
        return attrs


class TrainingSessionSerializer(serializers.ModelSerializer):
    attendance = AttendanceSerializer(many=True, read_only=True)

    class Meta:
        model = TrainingSession
        fields = [
            "id",
            "title",
            "held_on",
            "location",
            "trainer_name",
            "notes",
            "attendance",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "attendance"]


class TrainingSessionViewSet(OrgViewSet):
    queryset = TrainingSession.objects.prefetch_related("attendance__farmer")
    serializer_class = TrainingSessionSerializer
    write_roles = TRAIN
    search_fields = ("title", "trainer_name")


class TrainingMaterialViewSet(OrgViewSet):
    queryset = TrainingMaterial.objects.select_related("session")
    serializer_class = TrainingMaterialSerializer
    write_roles = TRAIN
    org_field = None
    org_lookup = "session__organization"


class AttendanceViewSet(OrgViewSet):
    queryset = Attendance.objects.select_related("session", "farmer")
    serializer_class = AttendanceSerializer
    write_roles = TRAIN
    org_field = None
    org_lookup = "session__organization"
    farmer_lookup = "farmer__user"
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset

    write_roles = TRAIN


# Farmers can read attendance. Creating stays with trainers via write_roles.
_ = OPERATIONS
