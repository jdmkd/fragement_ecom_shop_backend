from rest_framework import serializers
from django.utils import timezone


from .models import Warehouse, Inventory, InventoryTransaction
from orders.models import Order
from shipping.models import Shipment
from catalog.models import ProductVariant
from catalog.serializers import ProductVariantSerializer

class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = ["id", "code", "name", "address", "location_code",
                  "contact_person", "timezone", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class InventorySerializer(serializers.ModelSerializer):
    variant = ProductVariantSerializer(read_only=True)
    variant_id = serializers.PrimaryKeyRelatedField(
        queryset=Inventory._meta.get_field("variant").related_model.objects.all(),
        source="variant",
        write_only=True
    )
    warehouse = WarehouseSerializer(read_only=True)
    warehouse_id = serializers.PrimaryKeyRelatedField(
        queryset=Warehouse.objects.all(),
        source="warehouse",
        write_only=True
    )
    available = serializers.SerializerMethodField()

    class Meta:
        model = Inventory
        fields = [
            "id", "variant", "variant_id", "warehouse", "warehouse_id",
            "on_hand", "reserved", "allocated", "incoming", "safety_stock",
            "lot", "batch_number", "manufactured_date", "expiration_date",
            "uom", "status", "metadata", "available",
            "created_at", "updated_at"
        ]
        read_only_fields = ["id", "created_at", "updated_at", "available"]

    def get_available(self, obj):
        return obj.available()


class InventoryTransactionSerializer(serializers.ModelSerializer):
    variant = ProductVariantSerializer(read_only=True)
    warehouse = WarehouseSerializer(read_only=True)

    class Meta:
        model = InventoryTransaction
        fields = [
            "id", "transaction_type", "variant", "warehouse",
            "quantity_delta", "resulting_on_hand",
            "resulting_reserved", "resulting_allocated",
            "cost_price", "currency", "order", "shipment",
            "return_record", "reference", "source_document", "notes",
            "metadata", "created_by", "created_at", "updated_at"
        ]
        read_only_fields = ["id", "created_at", "updated_at"]



class InventoryActionSerializer(serializers.Serializer):
    qty = serializers.IntegerField(min_value=1)
    reference = serializers.CharField(max_length=255, required=False, allow_blank=True)
    # optional: link order/shipment by id (only allowed for admin/servers)
    order = serializers.PrimaryKeyRelatedField(queryset=Order.objects.all(), required=False)  # set in view
    shipment = serializers.PrimaryKeyRelatedField(queryset=Shipment.objects.all(), required=False)
    notes = serializers.CharField(max_length=255, required=False, allow_blank=True)
