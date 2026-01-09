import json
from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import Coalesce

from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from apps.users.models import UserProfile, UserPrivilege, Privilege
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    UserSerializer,
    UserProfileSerializer,
    ChangePasswordSerializer,
    LogoutSerializer,
)


# ---------------------------
# Privileges
# ---------------------------

class PrivilegeListView(APIView):
    # обычно тарифы/привилегии показывают до логина
    permission_classes = [AllowAny]

    def get(self, request):
        qs = Privilege.objects.all().order_by("price", "id")
        data = [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "price": str(p.price),
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in qs
        ]
        return Response(data, status=status.HTTP_200_OK)


class BuyPrivilegeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, privilege_id: int):
        privilege = Privilege.objects.filter(id=privilege_id).first()
        if not privilege:
            return Response({"detail": "Привилегия не найдена."}, status=status.HTTP_404_NOT_FOUND)

        _, created = UserPrivilege.objects.get_or_create(user=request.user, privilege=privilege)
        if not created:
            return Response({"detail": "Вы уже купили эту привилегию."}, status=status.HTTP_200_OK)

        return Response({"detail": "Куплено успешно."}, status=status.HTTP_201_CREATED)


class MyPrivilegesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = (
            UserPrivilege.objects
            .filter(user=request.user)
            .select_related("privilege")
            .order_by("-purchased_at")
        )
        data = [
            {
                "id": up.id,
                "privilege_id": up.privilege_id,
                "name": up.privilege.name,
                "description": up.privilege.description,
                "price": str(up.privilege.price),
                "purchased_at": up.purchased_at.isoformat() if up.purchased_at else None,
            }
            for up in qs
        ]
        return Response(data, status=status.HTTP_200_OK)


# ---------------------------
# Profile stats helper
# ---------------------------

class ProfileStatsMixin:
    def get_profile(self, user):
        profile, _ = UserProfile.objects.get_or_create(user=user)
        return profile

    def is_premium(self, user) -> bool:
        return UserPrivilege.objects.filter(user=user).exists()

    def calc_money_stats(self, user):
        from apps.management.models import Transaction

        income = Transaction.objects.filter(
            user=user, type=Transaction.INCOME
        ).aggregate(s=Coalesce(Sum("amount"), Decimal("0")))["s"]

        expense = Transaction.objects.filter(
            user=user, type=Transaction.EXPENSE
        ).aggregate(s=Coalesce(Sum("amount"), Decimal("0")))["s"]

        balance = income - expense
        operations_count = Transaction.objects.filter(user=user).count()

        economy_percent = 0
        if income > 0:
            economy_percent = int(((income - expense) / income) * 100)
            economy_percent = max(0, min(100, economy_percent))

        return {
            "balance": str(balance),
            "income_total": str(income),
            "expense_total": str(expense),
            "economy_percent": economy_percent,
            "operations_count": operations_count,
        }


# ---------------------------
# Auth
# ---------------------------

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        ser = RegisterSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = ser.save()
        return Response({"detail": "OK", "user_id": user.id}, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        ser = LoginSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        return Response(ser.validated_data, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """
    POST /auth/logout/  { "refresh": "..." }
    (Работает если подключен token_blacklist)
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = LogoutSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response({"detail": "OK"}, status=status.HTTP_200_OK)


# ---------------------------
# Me
# ---------------------------

class MeView(ProfileStatsMixin, APIView):
    """
    GET  /me/      -> профиль + статистика (как на экране)
    PATCH /me/     -> обновить user/profile

    Поддерживает:
    - JSON: {"user": {...}, "profile": {...}}
    - multipart/form-data:
        user = '{"first_name":"Ali"}'
        profile = '{"bio":"hi"}'
        avatar = <file>
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request):
        profile = self.get_profile(request.user)

        stats = self.calc_money_stats(request.user)
        premium = self.is_premium(request.user)

        return Response({
            "user": UserSerializer(request.user).data,
            "profile": UserProfileSerializer(profile, context={"request": request}).data,
            "is_premium": premium,
            "stats": {
                "goals_achieved": profile.goals_achieved,
                "saving_days": profile.saving_days,
                **stats,
            }
        }, status=status.HTTP_200_OK)

    def patch(self, request):
        profile = self.get_profile(request.user)

        user_data = request.data.get("user", {})
        profile_data = request.data.get("profile", {})

        # multipart часто присылает вложенные объекты строками
        if isinstance(user_data, str):
            try:
                user_data = json.loads(user_data)
            except Exception:
                user_data = {}

        if isinstance(profile_data, str):
            try:
                profile_data = json.loads(profile_data)
            except Exception:
                profile_data = {}

        # avatar отдельным полем (file)
        if "avatar" in request.FILES:
            profile_data["avatar"] = request.FILES["avatar"]

        user_ser = UserSerializer(request.user, data=user_data, partial=True)
        prof_ser = UserProfileSerializer(profile, data=profile_data, partial=True, context={"request": request})

        user_ser.is_valid(raise_exception=True)
        prof_ser.is_valid(raise_exception=True)

        user_ser.save()
        prof_ser.save()

        return Response({
            "user": user_ser.data,
            "profile": prof_ser.data
        }, status=status.HTTP_200_OK)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = ChangePasswordSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        old_password = ser.validated_data["old_password"]
        new_password = ser.validated_data["new_password"]

        if not request.user.check_password(old_password):
            return Response({"detail": "Старый пароль неверный"}, status=status.HTTP_400_BAD_REQUEST)

        request.user.set_password(new_password)
        request.user.save(update_fields=["password"])
        return Response({"detail": "Пароль обновлён"}, status=status.HTTP_200_OK)
