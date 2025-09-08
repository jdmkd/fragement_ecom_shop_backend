from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Cart, CartItem, PriceSnapshot
from .serializers import CartSerializer, CartItemSerializer, PriceSnapshotSerializer


class CartViewSet(viewsets.ModelViewSet):
    queryset = Cart.objects.all().select_related("user").prefetch_related("items")
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        """
        Automatically assign the logged-in user to the cart (if authenticated).
        Prevents clients from injecting arbitrary users.
        """
        serializer.save(user=self.request.user)

    def get_queryset(self):
        """
        Users can only see their own carts (unless admin).
        """
        user = self.request.user
        if user.is_staff:
            return Cart.objects.all()
        return Cart.objects.filter(user=user)

    @action(detail=True, methods=["post"], url_path="checkout")
    def checkout(self, request, pk=None):
        """
        Mark the cart as CHECKED_OUT.
        """
        cart = self.get_object()

        # Prevent double checkout
        if cart.status == "CHECKED_OUT":
            return Response(
                {"detail": "Cart already checked out."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cart.status = "CHECKED_OUT"
        cart.is_active = False
        cart.save(update_fields=["status", "is_active", "updated_at"])

        return Response(
            CartSerializer(cart, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )


class CartItemViewSet(viewsets.ModelViewSet):
    queryset = CartItem.objects.all().select_related("cart", "variant", "price_snapshot")
    serializer_class = CartItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Users can only see items from their own carts (unless admin).
        """
        user = self.request.user
        if user.is_staff:
            return CartItem.objects.all()
        return CartItem.objects.filter(cart__user=user)


class PriceSnapshotViewSet(viewsets.ModelViewSet):
    queryset = PriceSnapshot.objects.all()
    serializer_class = PriceSnapshotSerializer
    permission_classes = [permissions.IsAdminUser]  # Only staff can modify pricing
