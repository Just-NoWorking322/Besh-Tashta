import secrets

from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.models import OneTimeCode

User = get_user_model()


def gen_4digit() -> str:
    return f"{secrets.randbelow(10000):04d}"


def find_user_by_login(login: str):
    login = (login or "").strip().lower()
    if "@" in login:
        return User.objects.filter(email=login).first()
    return User.objects.filter(phone_number=login).first()


class PasswordResetRequestSerializer(serializers.Serializer):
    login = serializers.CharField()

    def save(self, **kwargs):
        user = find_user_by_login(self.validated_data["login"])

        # Не палим, существует ли юзер
        if not user:
            return

        code = gen_4digit()

        otp = OneTimeCode.create(user=user, purpose=OneTimeCode.PURPOSE_RESET, ttl_minutes=10)
        otp.set_code(code)
        otp.save()

        # отправляем на email пользователя
        send_mail(
            subject="Besh-Tashta: код для сброса пароля",
            message=f"Ваш код: {code}\nДействует 10 минут.",
            from_email=None,
            recipient_list=[user.email],
            fail_silently=False,
        )


class PasswordResetConfirmSerializer(serializers.Serializer):
    login = serializers.CharField()
    code = serializers.CharField(min_length=4, max_length=4)
    new_password = serializers.CharField(min_length=6, write_only=True)

    def validate(self, attrs):
        user = find_user_by_login(attrs["login"])
        if not user:
            raise serializers.ValidationError({"detail": "Invalid data"})

        otp = (
            OneTimeCode.objects.filter(
                user=user,
                purpose=OneTimeCode.PURPOSE_RESET,
                used_at__isnull=True,
            )
            .order_by("-created_at")
            .first()
        )
        if not otp:
            raise serializers.ValidationError({"code": "Code not found"})

        if otp.is_expired():
            raise serializers.ValidationError({"code": "Code expired"})

        if otp.attempts >= 5:
            raise serializers.ValidationError({"code": "Too many attempts"})

        if not otp.check_code(attrs["code"].strip()):
            otp.attempts += 1
            otp.save(update_fields=["attempts"])
            raise serializers.ValidationError({"code": "Invalid code"})

        attrs["user"] = user
        attrs["otp"] = otp
        return attrs

    def save(self, **kwargs):
        user = self.validated_data["user"]
        otp = self.validated_data["otp"]

        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])

        otp.used_at = timezone.now()
        otp.save(update_fields=["used_at"])


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        s = PasswordResetRequestSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        s.save()
        return Response({"detail": "If user exists, code sent"}, status=status.HTTP_200_OK)


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        s = PasswordResetConfirmSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        s.save()
        return Response({"detail": "Password changed"}, status=status.HTTP_200_OK)
