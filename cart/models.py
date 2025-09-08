from decimal import Decimal
from django.db import models
from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete
from django.db.models import Sum
from core.utils.common import TimeStampedModel


class Cart(TimeStampedModel):
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('CHECKED_OUT', 'Checked Out'),
        ('EXPIRED', 'Expired'),
    ]

    user = models.ForeignKey('accounts.User', null=True, blank=True, on_delete=models.CASCADE)
    session_id = models.CharField(max_length=128, null=True, blank=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    is_active = models.BooleanField(default=True)

    # Cached total for faster queries
    grand_total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        editable=False  # prevents editing in Django admin forms
    )

    class Meta:
        indexes = [
            models.Index(fields=['user', 'updated_at']),
            models.Index(fields=['session_id']),
        ]

    def recalc_total(self):
        """
        Recalculate and update grand_total by summing item line_totals.
        Uses aggregation for better performance.
        """
        total = self.items.aggregate(total=Sum("line_total"))["total"] or Decimal("0.00")
        self.grand_total = total
        self.save(update_fields=["grand_total", "updated_at"])

    def __str__(self):
        owner = self.user.email if self.user else f"Session {self.session_id}"
        return f"Cart #{self.pk} ({owner}) - {self.status}"


class PriceSnapshot(TimeStampedModel):
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=8, default='USD')
    breakdown = models.JSONField(default=dict, blank=True)  # taxes, discounts, promotions
    source = models.CharField(max_length=50, blank=True)   # e.g. catalog/discount
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.amount} {self.currency}"


class CartItem(TimeStampedModel):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey('catalog.ProductVariant', on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    price_snapshot = models.ForeignKey(PriceSnapshot, null=True, blank=True, on_delete=models.PROTECT)
    line_total = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = (('cart', 'variant'),)
        indexes = [
            models.Index(fields=['cart', 'variant']),
            models.Index(fields=['cart']),
        ]

    def save(self, *args, **kwargs):
        """
        Automatically compute line_total before saving.
        """
        if self.price_snapshot and self.price_snapshot.amount:
            self.line_total = Decimal(self.quantity) * self.price_snapshot.amount
        else:
            self.line_total = Decimal("0.00")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity} x {self.variant} (Cart #{self.cart.id})"


# -------------------
# SIGNALS
# -------------------

@receiver([post_save, post_delete], sender=CartItem)
def update_cart_total(sender, instance, **kwargs):
    """
    Keep Cart.grand_total in sync whenever CartItems change.
    """
    if instance.cart_id:
        instance.cart.recalc_total()
