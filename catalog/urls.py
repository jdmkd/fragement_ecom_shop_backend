# catalog/urls.py
from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import (
    CategoryViewSet, BrandViewSet, ProductViewSet, 
    ProductAttributeViewSet, ProductAttributeValueViewSet,
    ProductVariantViewSet, ProductImageViewSet
)

router = DefaultRouter()
router.register(r'categories', CategoryViewSet)
router.register(r'brands', BrandViewSet)
router.register(r'products', ProductViewSet)
router.register(r'product-attributes', ProductAttributeViewSet)
router.register(r'product-attribute-values', ProductAttributeValueViewSet)
router.register(r'product-variants', ProductVariantViewSet)
router.register(r'product-images', ProductImageViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
