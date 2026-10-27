from django.urls import path
from .auth_views import CsrfView, LoginView, LogoutView, RefreshView

from .views import (
    HealthView,
    OrderCreateView,
    TelemetryAggregateListView,
    TelemetryIngestView,
    TelemetryServiceListView,
)

urlpatterns = [
    path("auth/csrf/", CsrfView.as_view()), path("auth/login/", LoginView.as_view()),
    path("auth/refresh/", RefreshView.as_view()), path("auth/logout/", LogoutView.as_view()),
    path("health/", HealthView.as_view(), name="health"),
    path("orders/", OrderCreateView.as_view(), name="order-create"),
    path("telemetry/v1/", TelemetryIngestView.as_view(), name="telemetry-ingest-v1"),
    path("telemetry/v1/services/", TelemetryServiceListView.as_view(), name="telemetry-service-list-v1"),
    path("telemetry/v1/aggregates/", TelemetryAggregateListView.as_view(), name="telemetry-aggregate-list-v1"),
]

