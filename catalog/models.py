from django.db import models
from django.utils.text import slugify

from accounts.models import User
from core.utils.common import SoftDeleteModel, TimeStampedModel
from django.core.exceptions import ValidationError

def generate_unique_slug(model_class, field_value):
    """
    Generate a unique slug for a model by appending numbers if needed.
    """
    slug = slugify(field_value)
    unique_slug = slug
    counter = 1
    while model_class.objects.filter(slug=unique_slug).exists():
        unique_slug = f"{slug}-{counter}"
        counter += 1
    return unique_slug

class Category(TimeStampedModel, SoftDeleteModel):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, db_index=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT, related_name='children')
    image = models.ImageField(upload_to="categories/", null=True, blank=True)
    description = models.TextField(blank=True)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=['slug']), models.Index(fields=['name'])]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(Category, self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({'Root' if not self.parent else 'Child of ' + self.parent.name})"

class Brand(TimeStampedModel, SoftDeleteModel):
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True)
    logo = models.ImageField(upload_to="brands/", null=True, blank=True)
    description = models.TextField(blank=True)
    website_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(Brand, self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Product(TimeStampedModel, SoftDeleteModel):
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    categories = models.ManyToManyField(Category, related_name='products', blank=True)
    brand = models.ForeignKey(Brand, null=True, blank=True, on_delete=models.SET_NULL, related_name='products')
    default_variant = models.ForeignKey('ProductVariant', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    sku = models.CharField(max_length=64, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, db_index=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    description = models.TextField(blank=True)
    short_description = models.CharField(max_length=500, blank=True)
    search_keywords = models.TextField(blank=True)
    is_featured = models.BooleanField(default=False)
    is_listed = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)  
    is_active = models.BooleanField(default=True)
    # created_at = models.DateTimeField(auto_now_add=True)
    # updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=['sku', 'is_listed'])]

    def clean(self):
        if self.discount_price and self.discount_price > self.price:
            raise ValidationError("Discount price cannot be greater than base price.")

    @property
    def total_stock(self):
        return sum(v.stock_quantity for v in self.variants.all())
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(Product, self.name)
        super().save(*args, **kwargs)

        
    def __str__(self):
        return f"{self.sku} - {self.name}"

class ProductAttribute(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    display_name = models.CharField(max_length=100, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(ProductAttribute, self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.display_name or self.name

class ProductAttributeValue(TimeStampedModel):
    attribute = models.ForeignKey(ProductAttribute, on_delete=models.CASCADE, related_name='values')
    value = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = (('attribute','value'),('attribute','slug'))
        indexes = [models.Index(fields=['attribute'])]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(ProductAttributeValue, self.value)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.attribute.display_name}: {self.value}"

class ProductVariant(TimeStampedModel, SoftDeleteModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    sku = models.CharField(max_length=64, db_index=True)
    name = models.CharField(max_length=255) 
    price = models.DecimalField(max_digits=10, decimal_places=2)
    barcode = models.CharField(max_length=128, null=True, blank=True)
    attributes = models.JSONField(default=dict)  # canonical attribute map, e.g. {"size":"M","color":"red"}
    weight_kg = models.DecimalField(max_digits=9, decimal_places=3, null=True, blank=True)
    length_cm = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    width_cm = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    height_cm = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    stock_quantity = models.IntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ('product', 'sku')
        indexes = [models.Index(fields=['sku']), models.Index(fields=['product'])]
        constraints = [
            models.UniqueConstraint(fields=['product'], condition=models.Q(is_default=True), name="unique_default_variant_per_product")
        ]

    def __str__(self):
        return f"{self.sku} ({self.name})"

class ProductImage(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    variant = models.ForeignKey(ProductVariant, null=True, blank=True, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to="products/")
    is_primary = models.BooleanField(default=False)
    alt_text = models.CharField(max_length=255, blank=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['sort_order','-created_at']
        constraints = [
            models.UniqueConstraint(fields=['product'], condition=models.Q(is_primary=True), name="unique_primary_image_per_product")
        ]
    def __str__(self):
        return f"Image for {self.product} ({'Variant: ' + self.variant.sku if self.variant else 'All Variants'})"