from django.contrib import admin
from apps.notifications.models import Notification, CalendarEvent 


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "type", "title", "is_read", "created_at")
    list_filter = ("type", "is_read", "created_at")
    search_fields = ("title", "body", "user__email", "user__phone_number")
    ordering = ("-created_at", "-id")
    readonly_fields = ("created_at",)


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "title", "starts_at", "repeat", "reminder_minutes", "created_at")
    list_filter = ("repeat", "starts_at", "created_at")
    search_fields = ("title", "note", "user__email", "user__phone_number")
    ordering = ("-starts_at", "-id")
    readonly_fields = ("created_at", "updated_at")
