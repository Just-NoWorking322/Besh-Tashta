from django.conf import settings
from django.db import models


class CalendarEvent(models.Model):
    class Repeat(models.TextChoices):
        NONE = "NONE", "Не повторять"
        DAILY = "DAILY", "Каждый день"
        WEEKLY = "WEEKLY", "Каждую неделю"
        MONTHLY = "MONTHLY", "Каждый месяц"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="calendar_events")
    title = models.CharField(max_length=255)
    note = models.TextField(blank=True, default="")
    starts_at = models.DateTimeField()

    repeat = models.CharField(max_length=16, choices=Repeat.choices, default=Repeat.NONE)
    reminder_minutes = models.PositiveIntegerField(null=True, blank=True)  # например 10/60/1440

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-starts_at", "-id")

    def __str__(self):
        return f"{self.title} ({self.starts_at})"


class Notification(models.Model):
    class Type(models.TextChoices):
        CALENDAR = "CALENDAR", "Календарь"
        SYSTEM = "SYSTEM", "Система"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    type = models.CharField(max_length=32, choices=Type.choices, default=Type.SYSTEM)

    title = models.CharField(max_length=255)
    body = models.TextField(blank=True, default="")

    payload = models.JSONField(default=dict, blank=True)

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-id")

    def __str__(self):
        return f"[{self.type}] {self.title}"


class DeviceToken(models.Model):
    class Platform(models.TextChoices):
        ANDROID = "ANDROID", "Android"
        IOS = "IOS", "iOS"
        WEB = "WEB", "Web"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="device_tokens")
    token = models.CharField(max_length=512, unique=True)  # FCM token
    platform = models.CharField(max_length=16, choices=Platform.choices, default=Platform.ANDROID)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user_id} {self.platform}"