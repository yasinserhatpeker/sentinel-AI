from django.urls import include, path
from inventory.views import health
urlpatterns = [path("health/", health), path("v1/", include("inventory.urls"))]
