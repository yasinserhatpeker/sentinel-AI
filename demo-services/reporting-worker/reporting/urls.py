from django.urls import path
from .views import ReportJobDetailView, ReportJobListCreateView

urlpatterns = [path("reports/", ReportJobListCreateView.as_view()), path("reports/<int:pk>/", ReportJobDetailView.as_view())]
