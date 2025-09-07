# catalog/filters.py
import django_filters
from .models import Product, ProductVariant

class ProductFilter(django_filters.FilterSet):
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr="lte")
    brand = django_filters.CharFilter(field_name="brand__slug", lookup_expr="iexact")
    category = django_filters.CharFilter(field_name="subcategory__category__slug", lookup_expr="iexact")
    # subcategory = django_filters.CharFilter(field_name="subcategory__slug", lookup_expr="iexact")
    subcategory = django_filters.CharFilter(field_name="subcategory__slug", lookup_expr="iexact")


    color = django_filters.CharFilter(field_name="variants__color__name", lookup_expr="iexact")
    size = django_filters.CharFilter(field_name="variants__size__name", lookup_expr="iexact")

    class Meta:
        model = Product
        fields = ["brand", "category", "subcategory", "min_price", "max_price", "color", "size"]
