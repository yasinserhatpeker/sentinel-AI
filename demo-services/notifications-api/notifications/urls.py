from django.urls import path
from .views import NotificationDetailView, NotificationListCreateView

urlpatterns = [path("notifications/", NotificationListCreateView.as_view()), path("notifications/<int:pk>/", NotificationDetailView.as_view())]
