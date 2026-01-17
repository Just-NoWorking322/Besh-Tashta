from rest_framework import serializers
from .serializers import MotivationItemListSerializer

class DynamicTipSerializer(serializers.Serializer):
    type = serializers.CharField()
    code = serializers.CharField()
    title = serializers.CharField()
    short_text = serializers.CharField()
    icon = serializers.CharField()
    color = serializers.CharField()

class MotivationFeedResponseSerializer(serializers.Serializer):
    smart_hints = MotivationItemListSerializer(many=True)
    quote_of_day = MotivationItemListSerializer(allow_null=True)
    wish_of_day = MotivationItemListSerializer(allow_null=True)
    financial_tips = MotivationItemListSerializer(many=True)
    remember = MotivationItemListSerializer(many=True)
    dynamic = DynamicTipSerializer(many=True)