from rest_framework import serializers

# 1. Ответ при успешном логине/соц-входе
class AuthResponseSerializer(serializers.Serializer):
    access = serializers.CharField(help_text="JWT access token")
    refresh = serializers.CharField(help_text="JWT refresh token")

# 2. Ответ при регистрации (соответствует твоему коду)
class RegisterResponseSerializer(serializers.Serializer):
    detail = serializers.CharField(default="OK")
    user_id = serializers.IntegerField()

# 3. Вход через Google
class GoogleAuthRequestSerializer(serializers.Serializer):
    id_token = serializers.CharField(required=True)
    phone_number = serializers.CharField(required=False, allow_null=True)
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)

# 4. Вход через Apple
class AppleAuthRequestSerializer(serializers.Serializer):
    identity_token = serializers.CharField(required=True)
    email = serializers.EmailField(required=False)
    phone_number = serializers.CharField(required=False)
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)

# 5. Завершение соц. регистрации
class SocialCompleteRequestSerializer(serializers.Serializer):
    signup_token = serializers.CharField(required=True)
    phone_number = serializers.CharField(required=True)
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)

class MoneyStatsSerializer(serializers.Serializer):
    balance = serializers.CharField()
    income_total = serializers.CharField()
    expense_total = serializers.CharField()
    economy_percent = serializers.IntegerField()
    operations_count = serializers.IntegerField()
    goals_achieved = serializers.IntegerField(required=False)

class MeResponseSerializer(serializers.Serializer):
    from .serializers import UserSerializer, UserProfileSerializer
    user = UserSerializer()
    profile = UserProfileSerializer()
    is_premium = serializers.BooleanField()
    stats = MoneyStatsSerializer()

class PrivilegeResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    description = serializers.CharField()
    price = serializers.CharField()
    created_at = serializers.DateTimeField(required=False)
    purchased_at = serializers.DateTimeField(required=False)