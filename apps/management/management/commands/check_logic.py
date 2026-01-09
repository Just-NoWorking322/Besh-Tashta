from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from rest_framework.test import APIClient


def D(x) -> Decimal:
    return Decimal(str(x))


@dataclass
class Ctx:
    client: APIClient
    prefix: str
    today: str  # YYYY-MM-DD


class Command(BaseCommand):
    help = "E2E логический тест ключевых API (accounts/categories/transactions/debts/dashboard/stats)."

    def add_arguments(self, parser):
        parser.add_argument("--prefix", default="/api/v1", help="API prefix, например /api/v1")
        parser.add_argument("--keep-data", action="store_true", help="Не удалять созданные данные после теста")

    def handle(self, *args, **opts):
        prefix: str = opts["prefix"].rstrip("/")
        keep_data: bool = opts["keep_data"]

        User = get_user_model()
        uniq = uuid4().hex[:8]
        email = f"logic_{uniq}@test.local"
        phone = f"+996700{uniq[:6]}"  # просто чтобы было уникально
        password = "TestPass123!"

        user = None
        client = APIClient()

        try:
            user = User.objects.create_user(email=email, phone_number=phone, password=password)

            client.force_authenticate(user=user)            

            ctx = Ctx(
                client=client,
                prefix=prefix,
                today=timezone.localdate().isoformat(),
            )

            # 1) Dashboard должен создать дефолтный аккаунт
            dash1 = self._get(ctx, "/management/dashboard/")
            self._assert_decimal_eq(D(dash1["income_total"]), D("0"))
            self._assert_decimal_eq(D(dash1["expense_total"]), D("0"))
            self._assert_decimal_eq(D(dash1["balance"]), D("0"))

            # 2) Создаём категории (income/expense) уникальными именами
            cat_income = self._post(ctx, "/management/categories/", {
                "name": f"ЗП_{uniq}",
                "type": "INCOME",
            }, expected=(201,))

            cat_expense = self._post(ctx, "/management/categories/", {
                "name": f"Еда_{uniq}",
                "type": "EXPENSE",
            }, expected=(201,))

            # 3) Создаём транзакции: +1000, -200, -300 => balance = 500
            tx_in = self._post(ctx, "/management/transactions/", {
                "type": "INCOME",
                "amount": "1000",
                "title": "Зарплата",
                "category": cat_income["id"],
            }, expected=(201,))

            tx_e1 = self._post(ctx, "/management/transactions/", {
                "type": "EXPENSE",
                "amount": "200",
                "title": "Обед",
                "category": cat_expense["id"],
            }, expected=(201,))

            tx_e2 = self._post(ctx, "/management/transactions/", {
                "type": "EXPENSE",
                "amount": "300",
                "title": "Ужин",
                "category": cat_expense["id"],
            }, expected=(201,))

            # 4) Проверяем summary за сегодня
            summary = self._get(ctx, f"/management/stats/summary/?from={ctx.today}&to={ctx.today}")
            self._assert_decimal_eq(D(summary["income_total"]), D("1000"))
            self._assert_decimal_eq(D(summary["expense_total"]), D("500"))
            self._assert_decimal_eq(D(summary["balance"]), D("500"))

            # 5) Проверяем stats by category за сегодня
            by_cat = self._get(ctx, f"/management/stats/categories/?type=EXPENSE&from={ctx.today}&to={ctx.today}")
            items = by_cat["items"]
            # ищем нашу категорию
            mine = [i for i in items if i["category_id"] == cat_expense["id"]]
            if not mine:
                raise CommandError("Логика сломана: stats/categories не вернул нашу категорию расхода.")
            self._assert_decimal_eq(D(mine[0]["total"]), D("500"))

            # 6) Долг PAYABLE 700 и закрываем => добавится расход +700
            debt = self._post(ctx, "/management/debts/", {
                "kind": "PAYABLE",
                "amount": "700",
                "person_name": f"Кредит_{uniq}",
                "description": "Тест",
            }, expected=(201,))

            self._post(ctx, f"/management/debts/{debt['id']}/close/", {}, expected=(200,))

            # 7) Summary должен стать income=1000, expense=1200, balance=-200 (за сегодня)
            summary2 = self._get(ctx, f"/management/stats/summary/?from={ctx.today}&to={ctx.today}")
            self._assert_decimal_eq(D(summary2["income_total"]), D("1000"))
            self._assert_decimal_eq(D(summary2["expense_total"]), D("1200"))
            self._assert_decimal_eq(D(summary2["balance"]), D("-200"))

            # 8) /users/me/ должен отдать 200 (если у тебя там тоже статистика)
            self._get(ctx, "/users/me/")

            self.stdout.write(self.style.SUCCESS("✅ LOGIC CHECK OK: расчёты и основные сценарии совпали."))

        finally:
            # по умолчанию чистим тестового пользователя (и каскадные данные)
            if user and not keep_data:
                try:
                    user.delete()
                except Exception:
                    pass

    # ---------------- helpers ----------------

    def _url(self, ctx: Ctx, path: str) -> str:
        path = "/" + path.lstrip("/")
        return f"{ctx.prefix}{path}"

    def _get(self, ctx: Ctx, path: str, expected=(200,)):
        url = self._url(ctx, path)
        resp = ctx.client.get(url)
        if resp.status_code not in expected:
            raise CommandError(f"GET {url} -> {resp.status_code} | {getattr(resp, 'data', resp.content)}")
        return resp.data

    def _post(self, ctx: Ctx, path: str, data: dict, expected=(200, 201)):
        url = self._url(ctx, path)
        resp = ctx.client.post(url, data=data, format="json")
        if resp.status_code not in expected:
            raise CommandError(f"POST {url} -> {resp.status_code} | {getattr(resp, 'data', resp.content)}")
        return resp.data

    def _assert_decimal_eq(self, a: Decimal, b: Decimal):
        if a != b:
            raise CommandError(f"Логика сломана: ожидали {b}, получили {a}")
