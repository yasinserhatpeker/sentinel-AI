from django.urls import path
from .views import ReportJobDetailView, ReportJobListCreateView, WorkflowReportView

urlpatterns = [path("reports/", ReportJobListCreateView.as_view()), path("reports/<int:pk>/", ReportJobDetailView.as_view()), path("workflow/report/", WorkflowReportView.as_view())]
