from django.urls import path

from .views import PaymentAuthorizationDetailView, PaymentAuthorizationListCreateView, WorkflowAuthorizationView

urlpatterns = [path("authorizations/", PaymentAuthorizationListCreateView.as_view()), path("authorizations/<str:reference>/", PaymentAuthorizationDetailView.as_view()), path("workflow/authorize/", WorkflowAuthorizationView.as_view())]
