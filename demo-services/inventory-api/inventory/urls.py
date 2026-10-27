from django.urls import path
from .views import StockDetailView, StockListCreateView

urlpatterns = [path("stock/", StockListCreateView.as_view()), path("stock/<str:sku>/", StockDetailView.as_view())]
