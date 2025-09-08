from rest_framework import viewsets, filters
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404

from catalog.filters import ProductFilter

from .models import (
    Category, Brand, Product, ProductAttribute, ProductAttributeValue,
    ProductVariant, ProductImage
)
from .serializers import (
    CategorySerializer, BrandSerializer, ProductSerializer,
    ProductAttributeSerializer, ProductAttributeValueSerializer,
    ProductVariantSerializer, ProductImageSerializer
)
from core.utils.response_utils import api_response


class BaseViewSet(viewsets.ModelViewSet):
    """Common base viewset to apply standardized responses"""

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return api_response(data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return api_response(data=serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return api_response(data=serializer.data, message="Created successfully", status=201)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return api_response(data=serializer.data, message="Updated successfully")

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return api_response(data=None, message="Deleted successfully", status=204)


class CategoryViewSet(BaseViewSet):
    queryset = Category.objects.filter(is_active=True, deleted_at__isnull=True)
    serializer_class = CategorySerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['name']
    filterset_fields = ['is_active', 'is_featured']


class BrandViewSet(BaseViewSet):
    queryset = Brand.objects.filter(is_active=True, deleted_at__isnull=True)
    serializer_class = BrandSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['name']
    filterset_fields = ['is_active']


class ProductAttributeViewSet(BaseViewSet):
    queryset = ProductAttribute.objects.filter(is_active=True)
    serializer_class = ProductAttributeSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']


class ProductAttributeValueViewSet(BaseViewSet):
    queryset = ProductAttributeValue.objects.filter(is_active=True)
    serializer_class = ProductAttributeValueSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['value']


class ProductVariantViewSet(BaseViewSet):
    queryset = ProductVariant.objects.filter(is_active=True, deleted_at__isnull=True)
    serializer_class = ProductVariantSerializer


class ProductImageViewSet(BaseViewSet):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer


class ProductViewSet(BaseViewSet):
    queryset = Product.objects.filter(is_active=True, deleted_at__isnull=True)
    serializer_class = ProductSerializer

    lookup_field = "slug" # use slug instead of id
    lookup_value_regex = "[^/]+" # allows dots, hyphens, etc. in slug

    filter_backends = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'sku', 'brand__name', 'category__name']
    # filterset_fields = ['is_listed', 'is_featured', 'brand', 'categories']
    ordering_fields = ["price", "name", "created_at"]
    ordering = ['-created_at']

    @action(detail=True, methods=['get'])
    def variants(self, request, pk=None):
        product = self.get_object()
        serializer = ProductVariantSerializer(product.variants.all(), many=True)
        return api_response(data=serializer.data)

    @action(detail=True, methods=['get'])
    def images(self, request, pk=None):
        product = self.get_object()
        serializer = ProductImageSerializer(product.images.all(), many=True)
        return api_response(data=serializer.data)
