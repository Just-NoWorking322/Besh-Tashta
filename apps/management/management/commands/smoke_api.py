import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from rest_framework.test import APIClient

# твои модели
from apps.management.models import Account, Category, Transaction, Debt


@dataclass
class CheckResult:
    method: str
    path: str
    status_code: int
    ok: bool
    note: str = ""


class Command(BaseCommand):
    help = "Smoke test API endpoints (no 5xx). Optionally creates fixtures and tests with auth."

    def add_arguments(self, parser):
        parser.add_argument("--prefix", default="/api/v1", help="API prefix, default: /api/v1")
        parser.add_argument("--no-fixtures", action="store_true", help="Do not create minimal fixtures")
        parser.add_argument("--no-auth", action="store_true", help="Do not authenticate client")
        parser.add_argument("--strict", action="store_true", help="Fail on any 4xx (default: only fail on 5xx)")
        parser.add_argument("--quiet", action="store_true", help="Do not print each request line, only summary")

    def handle(self, *args, **opts):
        prefix: str = opts["prefix"].rstrip("/")
        create_fixtures: bool = not opts["no_fixtures"]
        use_auth: bool = not opts["no_auth"]
        strict: bool = opts["strict"]
        quiet: bool = opts["quiet"]

        # Убираем мусорные "Not Found:", "Bad Request:" из консоли
        logging.getLogger("django.request").setLevel(logging.ERROR)

        client = APIClient()
        # чтобы 500 не превращались в исключения при тесте
        client.raise_request_exception = False

        user = None
        if use_auth:
            user = self._get_any_user()
            if not user:
                raise CommandError("Нет пользователей в базе. Создай суперюзера: python manage.py createsuperuser")
            client.force_authenticate(user=user)

        ids = {}
        if create_fixtures and user:
            ids = self._ensure_fixtures(user)

        # Набор реальных эндпоинтов проекта (самый полезный минимум)
        # Здесь мы тестим GET/POST и detail по реальным id (если есть).
        endpoints = self._build_endpoints(prefix, ids)

        results: List[CheckResult] = []
        errors_5xx: List[CheckResult] = []
        errors_strict: List[CheckResult] = []

        for method, path, payload in endpoints:
            res = self._request(client, method, path, payload)

            ok = (res.status_code < 500)
            note = ""

            if strict and res.status_code >= 400:
                ok = False
                note = f"{res.status_code}"

            r = CheckResult(method=method, path=path, status_code=res.status_code, ok=ok, note=note)
            results.append(r)

            if res.status_code >= 500:
                errors_5xx.append(r)
            if strict and res.status_code >= 400:
                errors_strict.append(r)

            if not quiet:
                mark = "✅" if ok else "❌"
                self.stdout.write(f"{mark} {method:6} {path} -> {res.status_code}")

        self.stdout.write("")
        self.stdout.write(f"Проверено запросов: {len(results)}")
        self.stdout.write(f"5xx найдено: {len(errors_5xx)}")

        if strict:
            self.stdout.write(f"4xx/5xx ошибок (strict): {len(errors_strict)}")

        if errors_5xx:
            self.stdout.write("\n❌ Найдены 5xx:")
            for e in errors_5xx:
                self.stdout.write(f"- {e.method} {e.path} -> {e.status_code}")
            raise CommandError("Smoke test провален: есть 5xx.")

        if strict and errors_strict:
            self.stdout.write("\n❌ Strict ошибки (4xx/5xx):")
            for e in errors_strict[:20]:
                self.stdout.write(f"- {e.method} {e.path} -> {e.status_code}")
            raise CommandError("Smoke test провален в strict режиме.")

        self.stdout.write("\n✅ Smoke test OK: 5xx не найдено.")

    # -----------------------
    # helpers
    # -----------------------
    def _get_any_user(self):
        User = get_user_model()
        return User.objects.filter(is_active=True).order_by("-is_superuser", "id").first()

    def _ensure_fixtures(self, user) -> Dict[str, int]:
        # Account
        acc = Account.objects.filter(user=user).order_by("id").first()
        if not acc:
            acc = Account.objects.create(user=user, name="Основной", currency="KGS")

        # Category (минимально)
        cat = Category.objects.filter(user=user).order_by("id").first()
        if not cat:
            # если у тебя choice другой — поменяй значение "EXPENSE" на твоё
            cat = Category.objects.create(user=user, name="Тест категория", type="EXPENSE")

        # Transaction
        tx = Transaction.objects.filter(user=user).order_by("id").first()
        if not tx:
            # если у тебя choice другой — поменяй значения "EXPENSE"/"INCOME"
            tx = Transaction.objects.create(
                user=user,
                account=acc,
                category=cat,
                type="EXPENSE",
                amount=Decimal("10.00"),
                title="Smoke tx",
                note="",
                occurred_at=timezone.now(),
            )

        # Debt
        debt = Debt.objects.filter(user=user).order_by("id").first()
        if not debt:
            # если у Debt другие значения kind — поменяй "PAYABLE"
            debt = Debt.objects.create(
                user=user,
                kind="PAYABLE",
                amount=Decimal("100.00"),
                person_name="Smoke Person",
                description="",
                due_date=timezone.now().date(),
                is_closed=False,
            )

        return {
            "account_id": acc.id,
            "category_id": cat.id,
            "transaction_id": tx.id,
            "debt_id": debt.id,
        }

    def _build_endpoints(self, prefix: str, ids: Dict[str, int]) -> List[Tuple[str, str, Optional[Dict[str, Any]]]]:
        account_id = ids.get("account_id", 1)
        category_id = ids.get("category_id", 1)
        transaction_id = ids.get("transaction_id", 1)
        debt_id = ids.get("debt_id", 1)

        # payloads для POST (чтобы не было 400)
        payload_account = {"name": "Test Account", "currency": "KGS"}
        payload_category = {"name": "Test Category", "type": "EXPENSE"}
        payload_tx = {
            "account": account_id,
            "category": category_id,
            "type": "EXPENSE",
            "amount": "10.00",
            "title": "Test TX",
            "note": "",
            "occurred_at": timezone.now().isoformat(),
        }
        payload_debt = {
            "kind": "PAYABLE",
            "amount": "100.00",
            "person_name": "Test Person",
            "description": "",
            "due_date": timezone.now().date().isoformat(),
        }

        return [
            # Schema/Swagger (обычно только GET)
            ("GET", "/api/schema/", None),
            ("GET", "/api/swagger/", None),

            # Management
            ("GET", f"{prefix}/management/accounts/", None),
            ("POST", f"{prefix}/management/accounts/", payload_account),
            ("GET", f"{prefix}/management/accounts/{account_id}/", None),

            ("GET", f"{prefix}/management/categories/", None),
            ("POST", f"{prefix}/management/categories/", payload_category),
            ("GET", f"{prefix}/management/categories/{category_id}/", None),

            ("GET", f"{prefix}/management/transactions/", None),
            ("POST", f"{prefix}/management/transactions/", payload_tx),
            ("GET", f"{prefix}/management/transactions/{transaction_id}/", None),

            ("GET", f"{prefix}/management/debts/", None),
            ("POST", f"{prefix}/management/debts/", payload_debt),
            ("GET", f"{prefix}/management/debts/{debt_id}/", None),
            ("POST", f"{prefix}/management/debts/{debt_id}/close/", None),

            ("GET", f"{prefix}/management/dashboard/", None),
            ("GET", f"{prefix}/management/stats/summary/", None),
            ("GET", f"{prefix}/management/stats/categories/?type=EXPENSE", None),

            # Motivation
            ("GET", f"{prefix}/motivation/motivation/", None),

            # Users (тут без body будет 400 — поэтому либо давай payload, либо оставь только GET/OPTIONS)
            ("GET", f"{prefix}/users/me/", None),
        ]

    def _request(self, client: APIClient, method: str, path: str, payload: Optional[Dict[str, Any]]):
        method = method.upper()

        if method in ("POST", "PUT", "PATCH"):
            # ВАЖНО: format="json" -> решает 415 Unsupported Media Type
            return getattr(client, method.lower())(path, data=(payload or {}), format="json")

        return getattr(client, method.lower())(path)
