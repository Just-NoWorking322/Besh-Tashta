from decimal import Decimal
from urllib.parse import urlencode

from django.core.cache import cache
from django.db import transaction
from django.db.models import Sum, Q, Value, DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.dateparse import parse_date
from django_redis import get_redis_connection
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.motivation.ai import generate_motivation
from apps.notifications.services import create_and_send_notification


from .models import Account, Category, Transaction, Debt
from .serializers import (
    AccountSerializer,
    CategorySerializer,
    TransactionSerializer,
    DebtSerializer,
)

CACHE_TTL = 600  # 10 минту

ZERO = Value(Decimal("0"), output_field=DecimalField(max_digits=12, decimal_places=2))
# -------------------------
# Cache helpers
# -------------------------
def build_cache_key(prefix: str, user_id: int, params) -> str:
    """
    Делает стабильный ключ кэша на основе:
    - prefix (название эндпоинта)
    - user_id
    - query params (без refresh)
    """
    items = []
    for k, values in params.lists():
        if k == "refresh":
            continue
        for v in values:
            items.append((k, v))

    qs = urlencode(sorted(items), doseq=True)
    return f"mgmt:{prefix}:u{user_id}:{qs or 'noqs'}"


def invalidate_user_mgmt_cache(user_id: int) -> None:
    try:
        conn = get_redis_connection("default")
        for key in conn.scan_iter(match=f"mgmt:*:u{user_id}:*"):
            conn.delete(key)
    except Exception:
        pass


# -------------------------
# Mixins
# -------------------------
class DefaultAccountMixin:
    """
    Миксин: гарантирует что у юзера есть хотя бы один Account.
    """

    def get_or_create_default_account(self, user) -> Account:
        acc = Account.objects.filter(user=user).order_by("id").first()
        if not acc:
            acc = Account.objects.create(user=user, name="Основной", currency="KGS")
        return acc


class DateRangeFilterMixin:
    """
    Миксин: фильтр по датам.
    ?from=YYYY-MM-DD&to=YYYY-MM-DD
    """

    def apply_date_range(self, qs, request, field="occurred_at"):
        date_from = request.query_params.get("from")
        date_to = request.query_params.get("to")

        if date_from:
            d = parse_date(date_from)
            if d:
                qs = qs.filter(**{f"{field}__date__gte": d})

        if date_to:
            d = parse_date(date_to)
            if d:
                qs = qs.filter(**{f"{field}__date__lte": d})

        return qs


# -------------------------
# Dashboard (cached)
# -------------------------
class DashboardView(DefaultAccountMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        self.get_or_create_default_account(request.user)

        cache_key = build_cache_key("dashboard", request.user.id, request.query_params)

        # read cache (safe)
        if request.query_params.get("refresh") != "1":
            try:
                cached = cache.get(cache_key)
            except Exception:
                cached = None

            if cached is not None:
                resp = Response(cached)
                resp["X-Cache"] = "HIT"
                return resp

        income = Transaction.objects.filter(
            user=request.user, type=Transaction.INCOME
        ).aggregate(s=Coalesce(Sum("amount"), ZERO))["s"]

        expense = Transaction.objects.filter(
            user=request.user, type=Transaction.EXPENSE
        ).aggregate(s=Coalesce(Sum("amount"), ZERO))["s"]

        receivable = Debt.objects.filter(
            user=request.user, kind=Debt.RECEIVABLE, is_closed=False
        ).aggregate(s=Coalesce(Sum("amount"), ZERO))["s"]

        payable = Debt.objects.filter(
            user=request.user, kind=Debt.PAYABLE, is_closed=False
        ).aggregate(s=Coalesce(Sum("amount"), ZERO))["s"]

        last_transactions = (
            Transaction.objects.filter(user=request.user)
            .select_related("account", "category")
            .order_by("-occurred_at", "-id")[:10]
        )

        data = {
            "balance": str(income - expense),
            "income_total": str(income),
            "expense_total": str(expense),
            "debts": {"receivable": str(receivable), "payable": str(payable)},
            "last_transactions": TransactionSerializer(
                last_transactions, many=True, context={"request": request}
            ).data,
        }

        # write cache (safe)
        try:
            cache.set(cache_key, data, CACHE_TTL)
        except Exception:
            pass

        resp = Response(data)
        resp["X-Cache"] = "MISS"
        return resp


# -------------------------
# Accounts (CRUD + invalidate)
# -------------------------
class AccountListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AccountSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Account.objects.none()
        if not self.request.user.is_authenticated:
            return Account.objects.none()
        return Account.objects.filter(user=self.request.user).order_by("id")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        invalidate_user_mgmt_cache(self.request.user.id)


class AccountDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AccountSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Account.objects.none()
        if not self.request.user.is_authenticated:
            return Account.objects.none()
        return Account.objects.filter(user=self.request.user)

    def perform_update(self, serializer):
        serializer.save()
        invalidate_user_mgmt_cache(self.request.user.id)

    def perform_destroy(self, instance):
        instance.delete()
        invalidate_user_mgmt_cache(self.request.user.id)


# -------------------------
# Categories (CRUD + invalidate)
# -------------------------
class CategoryListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CategorySerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Category.objects.none()
        if not self.request.user.is_authenticated:
            return Category.objects.none()

        qs = Category.objects.filter(user=self.request.user).order_by("type", "name")
        type_ = self.request.query_params.get("type")  # INCOME/EXPENSE
        if type_:
            qs = qs.filter(type=type_)
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        invalidate_user_mgmt_cache(self.request.user.id)


class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CategorySerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Category.objects.none()
        if not self.request.user.is_authenticated:
            return Category.objects.none()
        return Category.objects.filter(user=self.request.user)

    def perform_update(self, serializer):
        serializer.save()
        invalidate_user_mgmt_cache(self.request.user.id)

    def perform_destroy(self, instance):
        instance.delete()
        invalidate_user_mgmt_cache(self.request.user.id)


# -------------------------
# Transactions (CRUD + invalidate)
# -------------------------
class TransactionListCreateView(
    DefaultAccountMixin, DateRangeFilterMixin, generics.ListCreateAPIView
):
    permission_classes = [IsAuthenticated]
    serializer_class = TransactionSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Transaction.objects.none()
        if not self.request.user.is_authenticated:
            return Transaction.objects.none()

        qs = (
            Transaction.objects.filter(user=self.request.user)
            .select_related("account", "category")
            .order_by("-occurred_at", "-id")
        )

        type_ = self.request.query_params.get("type")
        if type_:
            qs = qs.filter(type=type_)

        account_id = self.request.query_params.get("account")
        if account_id:
            qs = qs.filter(account_id=account_id)

        category_id = self.request.query_params.get("category")
        if category_id:
            qs = qs.filter(category_id=category_id)

        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(note__icontains=q))

        qs = self.apply_date_range(qs, self.request, field="occurred_at")
        return qs

    def perform_create(self, serializer):
        account = serializer.validated_data.get("account")
        if not account:
            account = self.get_or_create_default_account(self.request.user)

        tx = serializer.save(user=self.request.user, account=account)
        invalidate_user_mgmt_cache(self.request.user.id)

        title = (tx.title or "").lower()
        is_salary = tx.type == Transaction.INCOME and any(x in title for x in ["зп", "зарплата", "salary"])
        
        if is_salary:
            text = generate_motivation("salary_received", amount=tx.amount)
            create_and_send_notification(
                user=self.request.user,
                title="Мотивация",
                body=text,
                type_="SYSTEM",
                payload={"event": "salary_received", "tx_id": tx.id},
            )
        BIG_EXPENSE_THRESHOLD = Decimal("1000")  # можешь поменять

        is_big_expense = tx.type == Transaction.EXPENSE and tx.amount >= BIG_EXPENSE_THRESHOLD
        if is_big_expense:
            text = generate_motivation("big_expense", amount=tx.amount, ctx={"title": tx.title})
            create_and_send_notification(
                user=self.request.user,
                title="Мотивация",
                body=text,
                type_="SYSTEM",
                payload={"event": "big_expense", "tx_id": tx.id, "amount": str(tx.amount)},
            )


class TransactionDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TransactionSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Transaction.objects.none()
        if not self.request.user.is_authenticated:
            return Transaction.objects.none()

        return (
            Transaction.objects.filter(user=self.request.user)
            .select_related("account", "category")
        )

    def perform_update(self, serializer):
        serializer.save()
        invalidate_user_mgmt_cache(self.request.user.id)

    def perform_destroy(self, instance):
        instance.delete()
        invalidate_user_mgmt_cache(self.request.user.id)


# -------------------------
# Debts (CRUD + invalidate)
# -------------------------
class DebtListCreateView(DateRangeFilterMixin, generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DebtSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Debt.objects.none()
        if not self.request.user.is_authenticated:
            return Debt.objects.none()

        qs = Debt.objects.filter(user=self.request.user).order_by(
            "is_closed", "-created_at", "-id"
        )

        kind = self.request.query_params.get("kind")
        if kind:
            qs = qs.filter(kind=kind)

        is_closed = self.request.query_params.get("is_closed")
        if is_closed in ("true", "false"):
            qs = qs.filter(is_closed=(is_closed == "true"))

        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(Q(person_name__icontains=q) | Q(description__icontains=q))

        due_from = self.request.query_params.get("due_from")
        due_to = self.request.query_params.get("due_to")

        if due_from:
            d = parse_date(due_from)
            if d:
                qs = qs.filter(due_date__gte=d)

        if due_to:
            d = parse_date(due_to)
            if d:
                qs = qs.filter(due_date__lte=d)

        return qs

    def perform_create(self, serializer):
        debt = serializer.save(user=self.request.user)
        invalidate_user_mgmt_cache(self.request.user.id)

        
        event = "debt_created"
        text = generate_motivation(
            event,
            amount=debt.amount,
            ctx={
                "person_name": debt.person_name,
                "kind": debt.kind,  # PAYABLE / RECEIVABLE
                "due_date": getattr(debt, "due_date", None),
            },
        )
        create_and_send_notification(
            user=self.request.user,
            title="Мотивация",
            body=text,
            type_="SYSTEM",
            payload={"event": event, "debt_id": debt.id},
        )


class DebtDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DebtSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Debt.objects.none()
        if not self.request.user.is_authenticated:
            return Debt.objects.none()
        return Debt.objects.filter(user=self.request.user)

    def perform_update(self, serializer):
        serializer.save()
        invalidate_user_mgmt_cache(self.request.user.id)

    def perform_destroy(self, instance):
        instance.delete()
        invalidate_user_mgmt_cache(self.request.user.id)


class DebtCloseView(DefaultAccountMixin, APIView):
    """
    POST /debts/<id>/close/
    Закрывает долг и создаёт Transaction:
    - RECEIVABLE -> INCOME
    - PAYABLE -> EXPENSE
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk: int):
        debt = Debt.objects.filter(user=request.user, pk=pk).first()
        if not debt:
            return Response({"detail": "Долг не найден."}, status=status.HTTP_404_NOT_FOUND)

        if debt.is_closed:
            return Response({"detail": "Долг уже закрыт."}, status=status.HTTP_200_OK)

        # 1) закрываем долг
        debt.is_closed = True
        debt.closed_at = timezone.now()
        debt.save(update_fields=["is_closed", "closed_at"])

        # 2) добавляем в историю операций
        account = self.get_or_create_default_account(request.user)
        tx_type = Transaction.INCOME if debt.kind == Debt.RECEIVABLE else Transaction.EXPENSE

        Transaction.objects.create(
            user=request.user,
            account=account,
            category=None,
            type=tx_type,
            amount=debt.amount,
            title=f"Закрытие долга: {debt.person_name}",
            note=debt.description or "",
            occurred_at=timezone.now(),
        )
        text = generate_motivation(
            "debt_closed",
            amount=debt.amount,
            ctx={"person_name": debt.person_name},
        )

        create_and_send_notification(
            user=request.user,
            title="Мотивация",
            body=text,
            type_="SYSTEM",
            payload={"event": "debt_closed", "debt_id": debt.id},
        )

        invalidate_user_mgmt_cache(request.user.id)
        return Response({"detail": "Долг закрыт и добавлен в историю операций."}, status=status.HTTP_200_OK)
    

# -------------------------
# Stats (cached)
# -------------------------
class StatsSummaryView(DateRangeFilterMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cache_key = build_cache_key("stats_summary", request.user.id, request.query_params)

        if request.query_params.get("refresh") != "1":
            try:
                cached = cache.get(cache_key)
            except Exception:
                cached = None

            if cached is not None:
                resp = Response(cached)
                resp["X-Cache"] = "HIT"
                return resp

        qs = Transaction.objects.filter(user=request.user)
        qs = self.apply_date_range(qs, request, field="occurred_at")

        income = qs.filter(type=Transaction.INCOME).aggregate(
            s=Coalesce(Sum("amount"), ZERO)
        )["s"]
        expense = qs.filter(type=Transaction.EXPENSE).aggregate(
            s=Coalesce(Sum("amount"), ZERO)
        )["s"]

        data = {
            "income_total": str(income),
            "expense_total": str(expense),
            "balance": str(income - expense),
        }

        try:
            cache.set(cache_key, data, CACHE_TTL)
        except Exception:
            pass

        resp = Response(data)
        resp["X-Cache"] = "MISS"
        return resp


class StatsByCategoryView(DateRangeFilterMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cache_key = build_cache_key("stats_by_category", request.user.id, request.query_params)

        if request.query_params.get("refresh") != "1":
            try:
                cached = cache.get(cache_key)
            except Exception:
                cached = None

            if cached is not None:
                resp = Response(cached)
                resp["X-Cache"] = "HIT"
                return resp

        tx_type = request.query_params.get("type", Transaction.EXPENSE)
        qs = Transaction.objects.filter(user=request.user, type=tx_type)
        qs = self.apply_date_range(qs, request, field="occurred_at")

        rows = (
            qs.values("category_id", "category__name")
            .annotate(total=Coalesce(Sum("amount"), ZERO))
            .order_by("-total")
        )

        data = {
            "type": tx_type,
            "items": [
                {
                    "category_id": r["category_id"],
                    "category_name": r["category__name"] or "Без категории",
                    "total": str(r["total"]),
                }
                for r in rows
            ],
        }

        try:
            cache.set(cache_key, data, CACHE_TTL)
        except Exception:
            pass

        resp = Response(data)
        resp["X-Cache"] = "MISS"
        return resp
