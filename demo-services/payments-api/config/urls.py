from django.urls import include, path
from payments.views import health

urlpatterns = [path("health/", health), path("v1/", include("payments.urls"))]
