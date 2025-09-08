from rest_framework import serializers
from django.db import transaction
from .models import Order, OrderItem
from accounts.models import Address
from catalog.models import ProductVariant


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = [
            "id",
            "variant",
            "sku",
            "name",
            "quantity",
            "unit_price",
            "line_total",
            "tax_amount",
            "discount_amount",
        ]
        read_only_fields = ["id", "line_total"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    billing_address_id = serializers.PrimaryKeyRelatedField(
        queryset=Address.objects.all(),
        source="billing_address",
        write_only=True,
        required=False,
        allow_null=True,
    )
    shipping_address_id = serializers.PrimaryKeyRelatedField(
        queryset=Address.objects.all(),
        source="shipping_address",
        write_only=True,
        required=False,
        allow_null=True,
    )

    # Read-only snapshots for frontend display
    billing_address_snapshot = serializers.JSONField(read_only=True)
    shipping_address_snapshot = serializers.JSONField(read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "reference",
            "user",
            "status",
            "currency",
            "subtotal",
            "tax_total",
            "shipping_total",
            "discount_total",
            "total",
            "billing_address_id",
            "shipping_address_id",
            "billing_address_snapshot",
            "shipping_address_snapshot",
            "items",
            "placed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "reference",
            "user",
            "billing_address_snapshot",
            "shipping_address_snapshot",
            "placed_at",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        items_data = validated_data.pop("items", [])
        request = self.context.get("request")
        user = request.user if request and request.user.is_authenticated else None

        with transaction.atomic():
            order = Order.objects.create(user=user, **validated_data)

            subtotal = 0
            for item_data in items_data:
                variant = item_data["variant"]
                sku = variant.sku
                name = str(variant)
                quantity = item_data["quantity"]
                unit_price = item_data["unit_price"]
                tax_amount = item_data.get("tax_amount", 0)
                discount_amount = item_data.get("discount_amount", 0)

                # line_total = (unit_price * quantity) - item_data.get("discount_amount", 0) + item_data.get("tax_amount", 0)
                line_total = (unit_price * quantity) - discount_amount + tax_amount

                OrderItem.objects.create(
                    order=order,
                    variant=variant,
                    sku=sku,
                    name=name,
                    quantity=quantity,
                    unit_price=unit_price,
                    line_total=line_total,
                    tax_amount=tax_amount,
                    discount_amount=discount_amount,
                )
                subtotal += line_total

            # update totals
            order.subtotal = subtotal
            order.total = subtotal + order.shipping_total + order.tax_total - order.discount_total
            
            # Save address snapshots
            order.save_address_snapshots()
            order.save()

        return order

    def update(self, instance, validated_data):
        items_data = validated_data.pop("items", None)

        with transaction.atomic():
            # Update items only if order is in draft
            if items_data is not None:
                if instance.status != "draft":
                    raise serializers.ValidationError("Cannot modify items after order is placed.")

                # Remove existing items
                instance.items.all().delete()
                subtotal = 0

                for item_data in items_data:
                    variant = item_data["variant"]
                    sku = variant.sku
                    name = str(variant)
                    quantity = item_data["quantity"]
                    unit_price = item_data["unit_price"]
                    tax_amount = item_data.get("tax_amount", 0)
                    discount_amount = item_data.get("discount_amount", 0)

                    # line_total = (unit_price * quantity) - item_data.get("discount_amount", 0) + item_data.get("tax_amount", 0)
                    line_total = (unit_price * quantity) - discount_amount + tax_amount
                    
                    OrderItem.objects.create(
                        order=instance,
                        variant=variant,
                        sku=sku,
                        name=name,
                        quantity=quantity,
                        unit_price=unit_price,
                        line_total=line_total,
                        tax_amount=tax_amount,
                        discount_amount=discount_amount,
                    )
                    subtotal += line_total

                instance.subtotal = subtotal
                instance.total = subtotal + instance.shipping_total + instance.tax_total - instance.discount_total

            # Update allowed fields (billing/shipping/status/etc.)
            for attr, value in validated_data.items():
                setattr(instance, attr, value)

            # Update address snapshots
            instance.save_address_snapshots()
            instance.save()

        return instance
