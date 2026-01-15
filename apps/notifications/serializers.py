from rest_framework import serializers
from apps.notifications.models import CalendarEvent, Notification, DeviceToken


class CalendarEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarEvent
        fields = (
            "id",
            "title",
            "note",
            "starts_at",
            "repeat",
            "reminder_minutes",
            "created_at",
            "updated_at",
        )

    def create(self, validated_data):
        request = self.context["request"]
        return CalendarEvent.objects.create(user=request.user, **validated_data)


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ("id", "type", "title", "body", "payload", "is_read", "created_at")
        read_only_fields = ("id", "created_at")


class DeviceTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceToken
        fields = ("id", "token", "platform", "is_active", "created_at")
        read_only_fields = ("id", "created_at")