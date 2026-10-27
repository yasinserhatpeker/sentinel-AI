from django.urls import path

from .views import PaymentAuthorizationDetailView, PaymentAuthorizationListCreateView

urlpatterns = [path("authorizations/", PaymentAuthorizationListCreateView.as_view()), path("authorizations/<str:reference>/", PaymentAuthorizationDetailView.as_view())]
