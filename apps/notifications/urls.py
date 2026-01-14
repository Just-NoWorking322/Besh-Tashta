from django.urls import path
from .views import (
    EventListCreateView,
    EventDetailView,
    NotificationListView,
    NotificationReadView,
    NotificationReadAllView,
    DeviceTokenUpsertView,
    TestNotifyView
)

urlpatterns = [
    path("events/", EventListCreateView.as_view()),
    path("events/<int:pk>/", EventDetailView.as_view()),

    path("notifications/", NotificationListView.as_view()),
    path("notifications/<int:pk>/read/", NotificationReadView.as_view()),
    path("notifications/read-all/", NotificationReadAllView.as_view()),
    path("devices/", DeviceTokenUpsertView.as_view()),
    path("test/", TestNotifyView.as_view()),
    path("", NotificationListView.as_view()),
    
]
