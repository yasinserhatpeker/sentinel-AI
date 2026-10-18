from django.urls import path

from .views import HealthView, OrderCreateView, TelemetryIngestView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("orders/", OrderCreateView.as_view(), name="order-create"),
    path("telemetry/v1/", TelemetryIngestView.as_view(), name="telemetry-ingest-v1"),
]

