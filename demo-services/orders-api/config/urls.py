from django.urls import include, path
from orders.views import health
urlpatterns = [path("health/", health), path("v1/", include("orders.urls"))]
