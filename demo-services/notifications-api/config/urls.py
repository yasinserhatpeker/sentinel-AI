from django.urls import include, path
from notifications.views import health
urlpatterns = [path("health/", health), path("v1/", include("notifications.urls"))]
