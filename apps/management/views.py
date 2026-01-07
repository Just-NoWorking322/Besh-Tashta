from decimal import Decimal

from django.db import transaction
from django.db.models import Sum, Q
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.dateparse import parse_date

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Account, Category, Transaction, Debt
from .serializers import (
    AccountSerializer,
    CategorySerializer,
    TransactionSerializer,
    DebtSerializer,
)


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
# Dashboard
# -------------------------
class DashboardView(DefaultAccountMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        self.get_or_create_default_account(request.user)

        income = Transaction.objects.filter(
            user=request.user, type=Transaction.INCOME
        ).aggregate(s=Coalesce(Sum("amount"), Decimal("0")))["s"]

        expense = Transaction.objects.filter(
            user=request.user, type=Transaction.EXPENSE
        ).aggregate(s=Coalesce(Sum("amount"), Decimal("0")))["s"]

        receivable = Debt.objects.filter(
            user=request.user, kind=Debt.RECEIVABLE, is_closed=False
        ).aggregate(s=Coalesce(Sum("amount"), Decimal("0")))["s"]

        payable = Debt.objects.filter(
            user=request.user, kind=Debt.PAYABLE, is_closed=False
        ).aggregate(s=Coalesce(Sum("amount"), Decimal("0")))["s"]

        last_transactions = (
            Transaction.objects.filter(user=request.user)
            .select_related("account", "category")
            .order_by("-occurred_at", "-id")[:10]
        )

        return Response({
            "balance": str(income - expense),
            "income_total": str(income),
            "expense_total": str(expense),
            "debts": {
                "receivable": str(receivable),
                "payable": str(payable),
            },
            "last_transactions": TransactionSerializer(
                last_transactions, many=True, context={"request": request}
            ).data,
        })


# -------------------------
# Accounts
# -------------------------
class AccountListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AccountSerializer

    def get_queryset(self):
        return Account.objects.filter(user=self.request.user).order_by("id")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AccountDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AccountSerializer

    def get_queryset(self):
        return Account.objects.filter(user=self.request.user)


# -------------------------
# Categories
# -------------------------
class CategoryListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CategorySerializer

    def get_queryset(self):
        qs = Category.objects.filter(user=self.request.user).order_by("type", "name")
        type_ = self.request.query_params.get("type")  # INCOME/EXPENSE
        if type_:
            qs = qs.filter(type=type_)
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CategorySerializer

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)


# -------------------------
# Transactions
# -------------------------
class TransactionListCreateView(DefaultAccountMixin, DateRangeFilterMixin, generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TransactionSerializer

    def get_queryset(self):
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
        self.get_or_create_default_account(self.request.user)
        serializer.save(user=self.request.user)


class TransactionDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TransactionSerializer

    def get_queryset(self):
        return (
            Transaction.objects.filter(user=self.request.user)
            .select_related("account", "category")
        )


# -------------------------
# Debts
# -------------------------
class DebtListCreateView(DateRangeFilterMixin, generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DebtSerializer

    def get_queryset(self):
        qs = Debt.objects.filter(user=self.request.user).order_by("is_closed", "-created_at", "-id")

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
        serializer.save(user=self.request.user)


class DebtDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DebtSerializer

    def get_queryset(self):
        return Debt.objects.filter(user=self.request.user)


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

        return Response({"detail": "Долг закрыт и добавлен в историю операций."}, status=status.HTTP_200_OK)


# -------------------------
# Stats
# -------------------------
class StatsSummaryView(DateRangeFilterMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Transaction.objects.filter(user=request.user)
        qs = self.apply_date_range(qs, request, field="occurred_at")

        income = qs.filter(type=Transaction.INCOME).aggregate(
            s=Coalesce(Sum("amount"), Decimal("0"))
        )["s"]
        expense = qs.filter(type=Transaction.EXPENSE).aggregate(
            s=Coalesce(Sum("amount"), Decimal("0"))
        )["s"]

        return Response({
            "income_total": str(income),
            "expense_total": str(expense),
            "balance": str(income - expense),
        })


class StatsByCategoryView(DateRangeFilterMixin, APIView):
    """
    /stats/categories/?type=EXPENSE&from=YYYY-MM-DD&to=YYYY-MM-DD
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tx_type = request.query_params.get("type", Transaction.EXPENSE)

        qs = Transaction.objects.filter(user=request.user, type=tx_type)
        qs = self.apply_date_range(qs, request, field="occurred_at")

        rows = (
            qs.values("category_id", "category__name")
            .annotate(total=Coalesce(Sum("amount"), Decimal("0")))
            .order_by("-total")
        )

        items = [
            {
                "category_id": r["category_id"],
                "category_name": r["category__name"] or "Без категории",
                "total": str(r["total"]),
            }
            for r in rows
        ]

        return Response({"type": tx_type, "items": items})


from django.core.cache import cache

def get_analytics(payload: dict):
    cache_key = f"management:analytics:{hash(str(sorted(payload.items())))}"
    cached = cache.get(cache_key)
    if cached is not None:
        return {"cached": True, "data": cached}

    data = {
        "totals": {},
        "groups": {},
    }

    cache.set(cache_key, data, timeout=600)  
    return {"cached": False, "data": data}
