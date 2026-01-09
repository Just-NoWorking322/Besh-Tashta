from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal


class Account(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="accounts")
    name = models.CharField(max_length=100, default="Основной")
    currency = models.CharField(max_length=5, default="KGS")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Счёт"
        verbose_name_plural = "Счета"

    def __str__(self):
        return f"{self.name} ({self.currency})"


class Category(models.Model):
    TYPE_INCOME = "INCOME"
    TYPE_EXPENSE = "EXPENSE"
    TYPE_CHOICES = (
        (TYPE_INCOME, "Доход"),
        (TYPE_EXPENSE, "Расход"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="categories")
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=TYPE_EXPENSE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        constraints = [
            models.UniqueConstraint(fields=["user", "name", "type"], name="uniq_user_category_name_type")
        ]

    def __str__(self):
        return f"{self.name} ({self.type})"

class Transaction(models.Model):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"

    TYPE_CHOICES = (
        (INCOME, "Доход"),
        (EXPENSE, "Расход"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    account = models.ForeignKey("Account", on_delete=models.CASCADE)
    category = models.ForeignKey("Category", null=True, blank=True, on_delete=models.SET_NULL)

    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    title = models.CharField(max_length=255, blank=True, default="")
    note = models.TextField(blank=True, default="")
    occurred_at = models.DateTimeField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.type} {self.amount}"


class Debt(models.Model):
    RECEIVABLE = "RECEIVABLE"  
    PAYABLE = "PAYABLE"       
    KIND_CHOICES = (
        (RECEIVABLE, "Мне должны"),
        (PAYABLE, "Я должен"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="debts")
    kind = models.CharField(max_length=12, choices=KIND_CHOICES)

    person_name = models.CharField(max_length=120)  
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])

    due_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True, default="")

    is_closed = models.BooleanField(default=False)
    closed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Долг"
        verbose_name_plural = "Долги"
        ordering = ["is_closed", "-created_at", "-id"]

    def __str__(self):
        return f"{self.kind}: {self.person_name} {self.amount}"
