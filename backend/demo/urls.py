from django.urls import path

from .views import HealthView, OrderCreateView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("orders/", OrderCreateView.as_view(), name="order-create"),
]

