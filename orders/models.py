from django.db import models
from django.utils import timezone
from django.db import transaction

from core.utils.common import TimeStampedModel

ORDER_STATUS = [
    ('draft','Draft'),
    ("pending", "Pending"),
    ('confirmed','Confirmed'),
    ('processing','Processing'),
    ('shipped','Shipped'),
    ('delivered','Delivered'),
    ('cancelled','Cancelled'),
    ('returned','Returned'),
    ('refunded','Refunded')
]

class Order(TimeStampedModel):
    user = models.ForeignKey('accounts.User', null=True, blank=True, on_delete=models.SET_NULL)
    reference = models.CharField(max_length=64, unique=True, db_index=True)
    status = models.CharField(max_length=32, choices=ORDER_STATUS, default='draft', db_index=True)
    currency = models.CharField(max_length=8, default='INR')

    # Pricing fields (keep subtotal, shipping, discount, tax, total)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tax_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    shipping_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    discount_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    # Proper Address relations
    billing_address = models.ForeignKey(
        'accounts.Address', 
        related_name='billing_orders',
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    shipping_address = models.ForeignKey(
        'accounts.Address',
        related_name='shipping_orders',
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    
    # Address snapshots (immutable copies at time of order)
    billing_address_snapshot = models.JSONField(default=dict, blank=True)
    shipping_address_snapshot = models.JSONField(default=dict, blank=True)

    placed_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [models.Index(fields=['user','status','placed_at'])]
        ordering = ['-placed_at', '-created_at']

    def save_address_snapshots(self):
        """Copy current Address objects into snapshots."""
        if self.billing_address:
            self.billing_address_snapshot = {
                "first_name": self.billing_address.first_name,
                "last_name": self.billing_address.last_name,
                "street_address": self.billing_address.street_address,
                "city": self.billing_address.city,
                "state": self.billing_address.state,
                "postal_code": self.billing_address.postal_code,
                "country": self.billing_address.country,
                "phone": self.billing_address.phone,
            }

        if self.shipping_address:
            self.shipping_address_snapshot = {
                "first_name": self.shipping_address.first_name,
                "last_name": self.shipping_address.last_name,
                "street_address": self.shipping_address.street_address,
                "city": self.shipping_address.city,
                "state": self.shipping_address.state,
                "postal_code": self.shipping_address.postal_code,
                "country": self.shipping_address.country,
                "phone": self.shipping_address.phone,
            }
            
    def place_order(self, *, do_allocate=True, user=None):
        from inventory.models import Inventory, InventoryTransaction

        if self.status != 'draft':
            raise Exception('Only draft orders can be placed')

        if do_allocate:
            with transaction.atomic():
                for item in self.items.select_for_update():
                    qty = item.quantity
                    inv = Inventory.objects.filter(variant=item.variant).select_for_update().order_by('-on_hand').first()
                    if not inv or inv.available() < qty:
                        raise Exception(f'Insufficient stock for {item.variant.sku}')
                    inv.reserved += qty
                    inv.save()
                    InventoryTransaction.objects.create(
                        transaction_type='allocation',
                        variant=item.variant,
                        warehouse=inv.warehouse,
                        quantity_delta=-qty,
                        resulting_on_hand=inv.on_hand,
                        resulting_reserved=inv.reserved,
                        reference=self.reference,
                        created_by=user
                    )

        self.status = 'placed'
        self.placed_at = timezone.now()
        self.save()

    def __str__(self):
        return f"Order {self.id} - {self.user.email if self.user else 'Guest'} - {self.status}"


class OrderItem(TimeStampedModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey('catalog.ProductVariant', on_delete=models.PROTECT)
    sku = models.CharField(max_length=64)
    name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=14, decimal_places=2)
    line_total = models.DecimalField(max_digits=14, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        indexes = [models.Index(fields=['order']), models.Index(fields=['variant'])]
    
    def save(self, *args, **kwargs):
        self.line_total = (self.unit_price * self.quantity) - self.discount_amount + self.tax_amount
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} x {self.quantity}"

class OrderEvent(TimeStampedModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='events')
    event_type = models.CharField(max_length=128)
    data = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey('accounts.User', null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.event_type} - Order {self.order.id}"


class Allocation(TimeStampedModel):
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, related_name='allocations')
    inventory = models.ForeignKey('inventory.Inventory', on_delete=models.PROTECT)
    quantity = models.BigIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['order_item', 'inventory'], name='unique_allocation_per_inventory')
        ]

    def __str__(self):
        return f"Allocation {self.quantity} of {self.order_item.name}"
