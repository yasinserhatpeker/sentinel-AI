from django.urls import include, path
from payments.views import health
from common.control import fault_control

urlpatterns = [path("health/", health), path("_internal/fault-control/", fault_control), path("v1/", include("payments.urls"))]
