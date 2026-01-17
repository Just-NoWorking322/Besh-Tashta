from django.utils import timezone
from django.db.models import Sum
from decimal import Decimal

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import generics

from .models import MotivationItem
from .serializers import MotivationItemListSerializer, MotivationItemDetailSerializer
from .serializers_swagger import MotivationFeedResponseSerializer
from drf_spectacular.utils import extend_schema

class DailyPickMixin:
    """
    Детерминированный выбор "цитаты дня"/"пожелания дня":
    каждому юзеру будет попадаться один элемент в день (без хранения в БД).
    """

    def pick_daily(self, qs, user, salt: int = 0):
        items = list(qs)
        if not items:
            return None
        today_seed = timezone.localdate().toordinal()
        idx = (today_seed + user.id + salt) % len(items)
        return items[idx]


class MotivationFeedView(DailyPickMixin, APIView):
    permission_classes = [IsAuthenticated]
    @extend_schema(
        tags=['Motivation'],
        summary="Главная лента мотивации и советов",
        description="Возвращает цитату дня, советы и динамические карточки на основе баланса.",
        responses={200: MotivationFeedResponseSerializer}
    )
    def get(self, request):
        limit = int(request.query_params.get("limit", 10))

        base = MotivationItem.objects.filter(is_active=True)

        smart_hints = base.filter(type=MotivationItem.SMART_HINT)[:limit]
        fin_tips = base.filter(type=MotivationItem.FIN_TIP)[:limit]
        remember = base.filter(type=MotivationItem.REMEMBER)[:limit]

        quote_qs = base.filter(type=MotivationItem.QUOTE)[:200]
        wish_qs = base.filter(type=MotivationItem.WISH)[:200]

        quote = self.pick_daily(quote_qs, request.user, salt=1)
        wish = self.pick_daily(wish_qs, request.user, salt=2)

        # --- Динамические подсказки (по желанию, очень полезно для экранов "У вас мало средств") ---
        dynamic = []
        try:
            from apps.management.models import Transaction

            income = (Transaction.objects
                      .filter(user=request.user, type=Transaction.INCOME)
                      .aggregate(s=Sum("amount"))["s"] or Decimal("0"))
            expense = (Transaction.objects
                       .filter(user=request.user, type=Transaction.EXPENSE)
                       .aggregate(s=Sum("amount"))["s"] or Decimal("0"))
            balance = income - expense

            # Пример: если баланс низкий/минус — показываем карточку
            if balance <= 0:
                dynamic.append({
                    "type": "DYNAMIC",
                    "code": "LOW_BALANCE",
                    "title": "У вас мало средств!",
                    "short_text": "Пересмотрите расходы и попробуйте сократить необязательные покупки.",
                    "icon": "warning",
                    "color": "orange",
                })
        except Exception:
            pass

        ctx = {"request": request}
        return Response({
            "smart_hints": MotivationItemListSerializer(smart_hints, many=True, context=ctx).data,
            "quote_of_day": MotivationItemListSerializer(quote, context=ctx).data if quote else None,
            "wish_of_day": MotivationItemListSerializer(wish, context=ctx).data if wish else None,
            "financial_tips": MotivationItemListSerializer(fin_tips, many=True, context=ctx).data,
            "remember": MotivationItemListSerializer(remember, many=True, context=ctx).data,
            "dynamic": dynamic,
        })


class MotivationDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MotivationItemDetailSerializer

    def get_queryset(self):
        return MotivationItem.objects.filter(is_active=True)
