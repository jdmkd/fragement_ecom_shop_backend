from rest_framework.decorators import action
from rest_framework import mixins
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework import status
from django.shortcuts import get_object_or_404
from core.utils.response_utils import api_response
from .models import Order
from .serializers import OrderSerializer

class OrderViewSet(
        mixins.CreateModelMixin, 
        mixins.RetrieveModelMixin, 
        mixins.ListModelMixin, 
        GenericViewSet
    ):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by('-placed_at')

    def create(self, request, *args, **kwargs):
        payload = request.data.copy()

        if payload.get('from_cart'):
            cart = getattr(request.user, 'cart', None)
            if not cart or not cart.items.exists():
                return api_response(success=False, status=400, message='Cart is empty')
            
            items = []
            for ci in cart.items.all():
                price = getattr(ci.product, 'price', None)
                if price is None:
                    price = ci.product.get_price() if hasattr(ci.product, 'get_price') else 0
                items.append({
                    'variant': ci.variant.id if ci.variant else None,
                    'sku': ci.product.sku if hasattr(ci.product, 'sku') else '',
                    'name': ci.product.name,
                    'product': ci.product,
                    'quantity': ci.quantity,
                    'unit_price': price,
                    'line_total': price * ci.quantity,
                })
            payload['items'] = items

        serializer = self.get_serializer(data=payload, context={'request': request})
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            order = serializer.save(user=request.user)
            # Save address snapshots (immutable copy at time of order)
            order.save_address_snapshots()
            order.status = 'pending'
            order.placed_at = order.placed_at or order.created_at
            order.save()

            # (Optional) Clear cart after placing order
            if payload.get('from_cart') and hasattr(request.user, 'cart'):
                request.user.cart.items.all().delete()

        return api_response(
            message='Order placed successfully',
            data=OrderSerializer(order, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )

    def destroy(self, request, *args, **kwargs):
        """Cancel an order if it's still in draft or pending state."""
        order = self.get_object()
        if order.status not in ['draft', 'pending']:
            return api_response(success=False, status=400,
                                message='Cannot cancel order in current state')
        order.status = 'cancelled'
        order.save()
        return api_response(message='Order cancelled successfully')
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def status(self, request, pk=None):
        """
        Update order status (admin/staff only).
        Example: POST /orders/{id}/status/ { "status": "shipped" }
        """
        order = self.get_object()
        new_status = request.data.get('status')

        if not new_status or new_status not in dict(order._meta.get_field('status').choices):
            return api_response(success=False, status=400, message="Invalid status value")

        old_status = order.status
        order.status = new_status
        order.save()

        # Log the event
        OrderEvent.objects.create(
            order=order,
            event_type="status_changed",
            data={"from": old_status, "to": new_status},
            created_by=request.user
        )

        return api_response(
            message=f"Order status updated from {old_status} → {new_status}",
            data=OrderSerializer(order, context={'request': request}).data,
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def cancel(self, request, pk=None):
        """
        Customer-only: Cancel their own order
        POST /orders/{id}/cancel/
        """
        order = self.get_object()

        if order.user != request.user:
            return api_response(success=False, status=403, message="You cannot cancel this order")

        if order.status not in ['draft', 'pending']:
            return api_response(success=False, status=400, message="Order cannot be cancelled in current state")

        old_status = order.status
        order.status = 'cancelled'
        order.save()

        # Log the event
        OrderEvent.objects.create(
            order=order,
            event_type="order_cancelled",
            data={"from": old_status, "to": "cancelled"},
            created_by=request.user
        )

        return api_response(
            message="Order cancelled successfully",
            data=OrderSerializer(order, context={'request': request}).data,
            status=status.HTTP_200_OK
        )