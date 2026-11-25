from rest_framework import serializers

from api.access import OrgViewSet
from api.roles import INVENTORY
from inventory.models import InputApproval, InputProduct, StockMovement, Supplier
from inventory.services import approval_flags, assert_can_use, on_hand


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ["id", "name", "phone", "region", "notes", "created_at"]
        read_only_fields = ["id", "created_at"]


class InputProductSerializer(serializers.ModelSerializer):
    on_hand = serializers.SerializerMethodField()
    approvals = serializers.SerializerMethodField()

    class Meta:
        model = InputProduct
        fields = [
            "id",
            "name",
            "category",
            "unit",
            "reorder_level",
            "on_hand",
            "approvals",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "on_hand", "approvals"]

    def get_on_hand(self, obj):
        return on_hand(obj)

    def get_approvals(self, obj):
        member = self.context.get("membership")
        if member is None:
            return []
        return approval_flags(member.organization, obj)


class InputApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = InputApproval
        fields = ["id", "product", "standard", "status", "note", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs):
        member = self.context["membership"]
        product = attrs.get("product") or getattr(self.instance, "product", None)
        standard = attrs.get("standard") or getattr(self.instance, "standard", None)
        if product.organization_id != member.organization_id:
            raise serializers.ValidationError(
                {"product": "Input was not found in your organization."}
            )
        if standard.organization_id not in (None, member.organization_id):
            raise serializers.ValidationError({"standard": "Standard is not available."})
        return attrs


class StockMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = [
            "id",
            "product",
            "supplier",
            "activity",
            "kind",
            "quantity",
            "occurred_on",
            "reference",
            "notes",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs):
        member = self.context["membership"]
        product = attrs.get("product") or getattr(self.instance, "product", None)
        kind = attrs.get("kind") or getattr(self.instance, "kind", None)
        quantity = attrs.get("quantity", getattr(self.instance, "quantity", None))
        if product.organization_id != member.organization_id:
            raise serializers.ValidationError(
                {"product": "Input was not found in your organization."}
            )
        if kind in {StockMovement.Kind.IN, StockMovement.Kind.OUT} and quantity <= 0:
            raise serializers.ValidationError({"quantity": "Quantity must be greater than zero."})
        if kind == StockMovement.Kind.ADJUSTMENT and quantity == 0:
            raise serializers.ValidationError({"quantity": "An adjustment cannot be zero."})
        supplier = attrs.get("supplier", getattr(self.instance, "supplier", None))
        if supplier and supplier.organization_id != member.organization_id:
            raise serializers.ValidationError(
                {"supplier": "Supplier was not found in your organization."}
            )
        if kind == StockMovement.Kind.OUT:
            assert_can_use(member.organization, product)
        return attrs


class SupplierViewSet(OrgViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    write_roles = INVENTORY
    search_fields = ("name",)


class InputProductViewSet(OrgViewSet):
    queryset = InputProduct.objects.all()
    serializer_class = InputProductSerializer
    write_roles = INVENTORY
    search_fields = ("name", "category")


class InputApprovalViewSet(OrgViewSet):
    queryset = InputApproval.objects.select_related("product", "standard")
    serializer_class = InputApprovalSerializer
    write_roles = INVENTORY
    org_field = None
    org_lookup = "product__organization"


class StockMovementViewSet(OrgViewSet):
    queryset = StockMovement.objects.select_related("product", "supplier")
    serializer_class = StockMovementSerializer
    write_roles = INVENTORY
    stamp_user = "recorded_by"
