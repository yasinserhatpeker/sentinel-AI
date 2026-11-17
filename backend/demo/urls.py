from django.urls import path
from .auth_views import CsrfView, LoginView, LogoutView, RefreshView

from .views import (
    AnomalyDetailView,
    AnomalyListView,
    EvaluationListView,
    FaultExperimentListCreateView,
    FaultExperimentRepeatView,
    FaultExperimentStopView,
    HealthView,
    ModelActivateView,
    ModelListView,
    LstmPrototypeTrainView,
    ModelReadinessView,
    ModelTrainView,
    OrderCreateView,
    TelemetryAggregateListView,
    TelemetryIngestView,
    TelemetryServiceListView,
    SystemOverviewView,
)

urlpatterns = [
    path("auth/csrf/", CsrfView.as_view()), path("auth/login/", LoginView.as_view()),
    path("auth/refresh/", RefreshView.as_view()), path("auth/logout/", LogoutView.as_view()),
    path("health/", HealthView.as_view(), name="health"),
    path("orders/", OrderCreateView.as_view(), name="order-create"),
    path("telemetry/v1/", TelemetryIngestView.as_view(), name="telemetry-ingest-v1"),
    path("telemetry/v1/services/", TelemetryServiceListView.as_view(), name="telemetry-service-list-v1"),
    path("telemetry/v1/overview/", SystemOverviewView.as_view(), name="system-overview-v1"),
    path("telemetry/v1/aggregates/", TelemetryAggregateListView.as_view(), name="telemetry-aggregate-list-v1"),
    path("anomalies/v1/", AnomalyListView.as_view(), name="anomaly-list-v1"),
    path("anomalies/v1/<uuid:anomaly_id>/", AnomalyDetailView.as_view(), name="anomaly-detail-v1"),
    path("models/v1/", ModelListView.as_view(), name="model-list-v1"),
    path("models/v1/readiness/", ModelReadinessView.as_view(), name="model-readiness-v1"),
    path("models/v1/train/", ModelTrainView.as_view(), name="model-train-v1"),
    path("models/v1/<uuid:model_id>/activate/", ModelActivateView.as_view(), name="model-activate-v1"),
    path("models/v1/lstm-prototype/train/", LstmPrototypeTrainView.as_view(), name="lstm-prototype-train-v1"),
    path("fault-experiments/v1/", FaultExperimentListCreateView.as_view(), name="fault-experiment-list-create-v1"),
    path("fault-experiments/v1/<uuid:experiment_id>/stop/", FaultExperimentStopView.as_view(), name="fault-experiment-stop-v1"),
    path("fault-experiments/v1/<uuid:experiment_id>/repeat/", FaultExperimentRepeatView.as_view(), name="fault-experiment-repeat-v1"),
    path("evaluations/v1/", EvaluationListView.as_view(), name="evaluation-list-v1"),
]

