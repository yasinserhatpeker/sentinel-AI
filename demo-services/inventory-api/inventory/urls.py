from django.urls import path
from .views import StockDetailView, StockListCreateView, WorkflowReservationView

urlpatterns = [path("stock/", StockListCreateView.as_view()), path("stock/<str:sku>/", StockDetailView.as_view()), path("workflow/reserve/", WorkflowReservationView.as_view())]
