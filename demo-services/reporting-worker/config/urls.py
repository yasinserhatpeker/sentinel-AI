from django.urls import include, path
from reporting.views import health
urlpatterns = [path("health/", health), path("v1/", include("reporting.urls"))]
