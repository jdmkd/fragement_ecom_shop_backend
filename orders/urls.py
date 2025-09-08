from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import OrderViewSet

router = DefaultRouter()
router.register(r'', OrderViewSet, basename='orders')

urlpatterns = [
    path('', include(router.urls)),
]

# Optional: if you want to document custom actions explicitly
# Example endpoints:
# GET    /orders/             -> list orders for authenticated user
# POST   /orders/             -> create order
# GET    /orders/{id}/        -> retrieve order
# POST   /orders/{id}/cancel/ -> customer cancel order
# POST   /orders/{id}/status/ -> staff update order status
