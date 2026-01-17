from __future__ import annotations

import time
from typing import Any, Dict

import jwt
import requests
from django.conf import settings
from django.core import signing
from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from apps.users.models import SocialAccount
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from drf_spectacular.utils import OpenApiTypes, extend_schema
from .swagger_serializers import AuthResponseSerializer, SocialCompleteRequestSerializer, GoogleAuthRequestSerializer, AppleAuthRequestSerializer

class SocialAuthResponseSerializer(serializers.Serializer):
    access = serializers.CharField(help_text="Твой новенький Access токен")
    refresh = serializers.CharField(help_text="Refresh токен, чтобы обновлять сессию")

class GoogleRequestSerializer(serializers.Serializer):
    id_token = serializers.CharField(required=True, help_text="Google ID Token")
    phone_number = serializers.CharField(required=False)
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)

class AppleRequestSerializer(serializers.Serializer):
    identity_token = serializers.CharField(required=True)
    email = serializers.EmailField(required=False)
    phone_number = serializers.CharField(required=False)
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)

User = get_user_model()

SOCIAL_SIGN_SALT = "users.social.signup"
SOCIAL_SIGN_MAX_AGE = 600  # 10 минут


def issue_jwt(user) -> Dict[str, str]:
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


def get_google_client_id() -> str:
    return (
        getattr(settings, "GOOGLE_CLIENT_ID", "")
        or getattr(settings, "SOCIAL_AUTH_GOOGLE_CLIENT_ID", "")
        or ""
    )


def make_signup_token(payload: Dict[str, Any]) -> str:
    return signing.dumps(payload, salt=SOCIAL_SIGN_SALT)


def load_signup_token(token: str) -> Dict[str, Any]:
    return signing.loads(token, salt=SOCIAL_SIGN_SALT, max_age=SOCIAL_SIGN_MAX_AGE)


def normalize_phone(phone: str) -> str:
    return (phone or "").strip()


# ---------- Apple keys cache ----------
APPLE_KEYS_CACHE: Dict[str, Any] = {"ts": 0, "keys": None}


def _get_apple_keys() -> list[dict]:
    now = int(time.time())
    if APPLE_KEYS_CACHE["keys"] and now - APPLE_KEYS_CACHE["ts"] < 3600:
        return APPLE_KEYS_CACHE["keys"]

    r = requests.get("https://appleid.apple.com/auth/keys", timeout=10)
    r.raise_for_status()
    data = r.json()

    APPLE_KEYS_CACHE["keys"] = data.get("keys", [])
    APPLE_KEYS_CACHE["ts"] = now
    return APPLE_KEYS_CACHE["keys"]


def verify_apple_identity_token(identity_token: str, audience: str) -> Dict[str, Any]:
    header = jwt.get_unverified_header(identity_token)
    kid = header.get("kid")

    keys = _get_apple_keys()
    jwk = next((k for k in keys if k.get("kid") == kid), None)
    if not jwk:
        raise ValueError("Apple public key not found")

    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)

    payload = jwt.decode(
        identity_token,
        public_key,
        algorithms=["RS256"],
        audience=audience,
        issuer="https://appleid.apple.com",
    )
    return payload


def _email_verified_apple(payload: Dict[str, Any]) -> bool:
    ev = payload.get("email_verified")
    return ev in (True, "true", "True", 1, "1")


class GoogleAuthView(APIView):
    permission_classes = [AllowAny]
    @extend_schema(
        tags=['Social Auth'],
        request=GoogleAuthRequestSerializer,
        responses={200: AuthResponseSerializer}
    )
    def post(self, request):
        token = request.data.get("id_token")
        phone_number = normalize_phone(request.data.get("phone_number")) or None
        first_name = (request.data.get("first_name") or "").strip()
        last_name = (request.data.get("last_name") or "").strip()

        if not token:
            return Response({"detail": "id_token is required"}, status=status.HTTP_400_BAD_REQUEST)

        google_client_id = get_google_client_id()
        if not google_client_id:
            return Response({"detail": "GOOGLE_CLIENT_ID is not set"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            info = google_id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                google_client_id,
            )
        except Exception:
            return Response({"detail": "Invalid Google token"}, status=status.HTTP_400_BAD_REQUEST)

        google_sub = info.get("sub")
        email = (info.get("email") or "").strip().lower()

        if not google_sub:
            return Response({"detail": "Google token has no sub"}, status=status.HTTP_400_BAD_REQUEST)
        if not email:
            return Response({"detail": "Google token has no email"}, status=status.HTTP_400_BAD_REQUEST)
        if info.get("email_verified") is not True:
            return Response({"detail": "Google email is not verified"}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            sa = (
                SocialAccount.objects
                .select_for_update()
                .select_related("user")
                .filter(provider="google", uid=google_sub)
                .first()
            )
            if sa:
                return Response(issue_jwt(sa.user), status=status.HTTP_200_OK)

            user = User.objects.select_for_update().filter(email=email).first()
            if user:
                SocialAccount.objects.create(user=user, provider="google", uid=google_sub)
                return Response(issue_jwt(user), status=status.HTTP_200_OK)

            if phone_number and User.objects.filter(phone_number=phone_number).exists():
                return Response({"detail": "phone_number already used"}, status=status.HTTP_409_CONFLICT)

            user = User.objects.create_user(
                email=email,
                phone_number=phone_number,
                password=None,
                first_name=first_name,
                last_name=last_name,
                is_active=True,
            )

            SocialAccount.objects.create(user=user, provider="google", uid=google_sub)

        return Response(issue_jwt(user), status=status.HTTP_200_OK)


class AppleAuthView(APIView):
    permission_classes = [AllowAny]
    @extend_schema(
        tags=['Social Auth'],
        summary="Вход через Apple",
        request=AppleRequestSerializer,
        responses={200: AuthResponseSerializer}
    )
    def post(self, request):
        identity_token = request.data.get("identity_token")
        email_from_client = (request.data.get("email") or "").strip().lower()
        phone_number = normalize_phone(request.data.get("phone_number")) or None
        first_name = (request.data.get("first_name") or "").strip()
        last_name = (request.data.get("last_name") or "").strip()

        if not identity_token:
            return Response({"detail": "identity_token is required"}, status=status.HTTP_400_BAD_REQUEST)

        apple_client_id = getattr(settings, "APPLE_CLIENT_ID", "")
        if not apple_client_id:
            return Response({"detail": "APPLE_CLIENT_ID is not set"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            payload = verify_apple_identity_token(identity_token, apple_client_id)
        except Exception:
            return Response({"detail": "Invalid Apple token"}, status=status.HTTP_400_BAD_REQUEST)

        apple_sub = payload.get("sub")
        email = (payload.get("email") or email_from_client or "").strip().lower()

        if not apple_sub:
            return Response({"detail": "Apple token has no sub"}, status=status.HTTP_400_BAD_REQUEST)

        if payload.get("email") and not _email_verified_apple(payload):
            return Response({"detail": "Apple email is not verified"}, status=status.HTTP_400_BAD_REQUEST)

        if not email:
            email = f"apple_{apple_sub}@example.invalid"

        with transaction.atomic():
            sa = (
                SocialAccount.objects
                .select_for_update()
                .select_related("user")
                .filter(provider="apple", uid=apple_sub)
                .first()
            )
            if sa:
                return Response(issue_jwt(sa.user), status=status.HTTP_200_OK)

            user = User.objects.select_for_update().filter(email=email).first()
            if user:
                SocialAccount.objects.create(user=user, provider="apple", uid=apple_sub)
                return Response(issue_jwt(user), status=status.HTTP_200_OK)

            if phone_number and User.objects.filter(phone_number=phone_number).exists():
                return Response({"detail": "phone_number already used"}, status=status.HTTP_409_CONFLICT)

            user = User.objects.create_user(
                email=email,
                phone_number=phone_number,
                password=None,
                first_name=first_name,
                last_name=last_name,
                is_active=True,
            )

            SocialAccount.objects.create(user=user, provider="apple", uid=apple_sub)

        return Response(issue_jwt(user), status=status.HTTP_200_OK)


class SocialCompleteView(APIView):
    """
    POST /auth/social/complete/
    Body: {signup_token, phone_number, first_name?, last_name?}
    """
    permission_classes = [AllowAny]
    @extend_schema(
        tags=['Social Auth'],
        request=SocialCompleteRequestSerializer,
        responses={200: AuthResponseSerializer}
    )
    def post(self, request):
        token = request.data.get("signup_token")
        phone_number = normalize_phone(request.data.get("phone_number"))
        first_name = (request.data.get("first_name") or "").strip()
        last_name = (request.data.get("last_name") or "").strip()

        if not token:
            return Response({"detail": "signup_token is required"}, status=status.HTTP_400_BAD_REQUEST)
        if not phone_number:
            return Response({"detail": "phone_number is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            data = load_signup_token(token)
        except Exception:
            return Response({"detail": "Invalid or expired signup_token"}, status=status.HTTP_400_BAD_REQUEST)

        provider = data.get("provider")
        uid = data.get("uid")
        email = (data.get("email") or "").strip().lower()

        if provider not in ("google", "apple") or not uid:
            return Response({"detail": "Invalid signup_token payload"}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            sa = SocialAccount.objects.select_for_update().filter(provider=provider, uid=uid).select_related("user").first()
            if sa:
                return Response(issue_jwt(sa.user), status=status.HTTP_200_OK)

            if User.objects.filter(phone_number=phone_number).exists():
                return Response({"detail": "phone_number already used"}, status=status.HTTP_409_CONFLICT)

            if not email:
                email = f"{provider}_{uid}@example.invalid"

            if User.objects.filter(email=email).exists():
                # если вдруг email уже занят — считаем конфликт
                return Response({"detail": "email already used"}, status=status.HTTP_409_CONFLICT)

            # имена берем из токена, но если клиент прислал — предпочитаем клиента
            fn = first_name or (data.get("first_name") or "")
            ln = last_name or (data.get("last_name") or "")

            user = User.objects.create_user(
                email=email,
                phone_number=phone_number,
                password=None,
                first_name=fn,
                last_name=ln,
                is_active=True,
            )

            SocialAccount.objects.create(user=user, provider=provider, uid=uid)

        return Response(issue_jwt(user), status=status.HTTP_200_OK)
