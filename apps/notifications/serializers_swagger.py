from rest_framework import serializers

class NotificationResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    body = serializers.CharField()
    is_read = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    # Если есть ссылка на объект (например, на транзакцию или долг)
    target_id = serializers.IntegerField(required=False, allow_null=True)
    target_type = serializers.CharField(required=False)

class NotificationCountResponseSerializer(serializers.Serializer):
    unread_count = serializers.IntegerField()