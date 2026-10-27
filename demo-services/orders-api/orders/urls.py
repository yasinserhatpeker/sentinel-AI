from django.urls import path
from .views import OrderDetailView, OrderListCreateView

urlpatterns = [path("orders/", OrderListCreateView.as_view()), path("orders/<str:reference>/", OrderDetailView.as_view())]
