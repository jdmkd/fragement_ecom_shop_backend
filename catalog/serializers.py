from rest_framework import serializers
from .models import (
    Category, Brand, Product, ProductAttribute, ProductAttributeValue,
    ProductVariant, ProductImage
)


class CategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        exclude = ('deleted_at',)  # don’t expose soft delete field

    def get_children(self, obj):
        return CategorySerializer(obj.children.filter(is_active=True), many=True).data


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        exclude = ('deleted_at',)


class ProductAttributeValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductAttributeValue
        fields = "__all__"


class ProductAttributeSerializer(serializers.ModelSerializer):
    values = ProductAttributeValueSerializer(many=True, read_only=True)

    class Meta:
        model = ProductAttribute
        fields = "__all__"


class ProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        exclude = ('deleted_at',)


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = "__all__"


class ProductSerializer(serializers.ModelSerializer):
    categories = CategorySerializer(many=True, read_only=True)
    brand = BrandSerializer(read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    total_stock = serializers.ReadOnlyField()

    class Meta:
        model = Product
        exclude = ('deleted_at',)
