from rest_framework import serializers
from .models import Cart, CartItem, PriceSnapshot


class PriceSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceSnapshot
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at")


class CartItemSerializer(serializers.ModelSerializer):
    price_snapshot = PriceSnapshotSerializer(read_only=True)

    class Meta:
        model = CartItem
        fields = "__all__"
        read_only_fields = ("line_total", "created_at", "updated_at")


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)

    class Meta:
        model = Cart
        fields = "__all__"
        read_only_fields = ("grand_total", "created_at", "updated_at")
