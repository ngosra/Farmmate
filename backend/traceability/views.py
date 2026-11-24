import io

import qrcode
from django.http import HttpResponse
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from api.access import OrgViewSet, allow, require_membership
from api.audit import record
from api.roles import TRACE
from traceability.models import Batch, Movement
from traceability.services import add_movement, balance, open_batch


class BatchInputWriteSerializer(serializers.Serializer):
    harvest = serializers.UUIDField()
    quantity_kg = serializers.DecimalField(max_digits=12, decimal_places=3)


class BatchWriteSerializer(serializers.Serializer):
    product_name = serializers.CharField(max_length=200)
    inputs = BatchInputWriteSerializer(many=True)


class MovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movement
        fields = [
            "id",
            "kind",
            "quantity_kg",
            "loss_kg",
            "happened_on",
            "location",
            "notes",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class MovementWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movement
        fields = ["kind", "quantity_kg", "loss_kg", "happened_on", "location", "notes"]
        extra_kwargs = {
            "quantity_kg": {"required": False},
            "loss_kg": {"required": False},
            "location": {"required": False},
            "notes": {"required": False},
        }


class BatchSerializer(serializers.ModelSerializer):
    inputs = serializers.SerializerMethodField()
    movements = MovementSerializer(many=True, read_only=True)
    balance = serializers.SerializerMethodField()

    class Meta:
        model = Batch
        fields = [
            "id",
            "code",
            "public_code",
            "product_name",
            "status",
            "inputs",
            "movements",
            "balance",
            "created_at",
        ]

    def get_inputs(self, obj):
        return [
            {
                "id": str(row.id),
                "harvest": str(row.harvest_id),
                "quantity_kg": row.quantity_kg,
            }
            for row in obj.inputs.all()
        ]

    def get_balance(self, obj):
        return balance(obj)


def trace_payload(batch):
    data = BatchSerializer(batch).data
    data["verification"] = {
        "batch": batch.code,
        "product_name": batch.product_name,
        "status": batch.status,
        "organization": batch.organization.name,
    }
    return data


class BatchViewSet(OrgViewSet):
    queryset = Batch.objects.prefetch_related("inputs", "movements")
    serializer_class = BatchSerializer
    write_roles = TRACE
    http_method_names = ["get", "post", "head", "options"]

    def create(self, request, *args, **kwargs):
        from production.models import Harvest

        member = allow(request, TRACE)
        serializer = BatchWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        inputs = []
        for row in serializer.validated_data["inputs"]:
            harvest = Harvest.objects.filter(
                pk=row["harvest"], organization=member.organization
            ).first()
            if harvest is None:
                raise serializers.ValidationError(
                    {"inputs": "Harvest was not found in your organization."}
                )
            inputs.append({"harvest": harvest, "quantity_kg": row["quantity_kg"]})
        batch = open_batch(
            organization=member.organization,
            user=request.user,
            product_name=serializer.validated_data["product_name"],
            inputs=inputs,
        )
        record(request, "create", batch, f"Opened batch {batch.code}")
        return Response(BatchSerializer(batch).data, status=201)

    @action(detail=True, methods=["post"])
    def movements(self, request, pk=None):
        batch = self.get_object()
        allow(request, TRACE)
        serializer = MovementWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        movement = add_movement(batch, request.user, serializer.validated_data)
        record(request, "create", movement, f"{movement.kind} on {batch.code}")
        return Response(BatchSerializer(self.get_queryset().get(pk=batch.pk)).data, status=201)

    @action(detail=True, methods=["get"])
    def qr(self, request, pk=None):
        batch = self.get_object()
        image = qrcode.make(f"farmmate:batch:{batch.public_code}")
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return HttpResponse(buffer.getvalue(), content_type="image/png")


class TraceView(APIView):
    def get(self, request, public_code):
        member = require_membership(request)
        batch = (
            Batch.objects.filter(public_code=public_code, organization=member.organization)
            .prefetch_related("inputs", "movements")
            .first()
        )
        if batch is None:
            raise NotFound("No batch with that code was found in your organization.")
        return Response(trace_payload(batch))
