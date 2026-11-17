from django.urls import include, path
from notifications.views import health
from common.control import fault_control
urlpatterns = [path("health/", health), path("_internal/fault-control/", fault_control), path("v1/", include("notifications.urls"))]
