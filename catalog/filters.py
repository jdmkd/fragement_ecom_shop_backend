# catalog/filters.py
import django_filters
from .models import Category, Product, ProductVariant

class ProductFilter(django_filters.FilterSet):
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr="lte")
    brands = django_filters.CharFilter(field_name="brand__slug", lookup_expr="iexact")
    categories = django_filters.BaseInFilter(method="filter_by_categories")

    class Meta:
        model = Product
        fields = ["is_listed", "is_featured", "brands", "categories"]

    def filter_by_categories(self, queryset, name, value):
        """
        Filter products by category slug(s).
        - Default: include children categories.
        - If strict=true is in query params, filter only exact category.
        """
        request = self.request
        strict = request.query_params.get("strict", "false").lower() == "true"

        # collect category slugs to filter
        category_slugs = []
        for slug in value:
            try:
                cat = Category.objects.get(slug=slug, is_active=True, deleted_at__isnull=True)
                if strict:
                    category_slugs.append(cat.slug)
                else:
                    # include children recursively
                    descendants = cat.children.all()
                    all_slugs = [cat.slug] + list(descendants.values_list("slug", flat=True))
                    category_slugs.extend(all_slugs)
            except Category.DoesNotExist:
                continue

        return queryset.filter(categories__slug__in=category_slugs).distinct()

    class Meta:
        model = Product
        fields = ["is_listed", "is_featured", "brands", "categories", "min_price", "max_price"]