# apps/management/admin.py
from django.contrib import admin
from .models import Account, Category, Transaction, Debt

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "name", "currency", "created_at")
    search_fields = ("name", "user__email", "user__phone_number")
    list_filter = ("currency",)
    ordering = ("-id",)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "name", "type")
    search_fields = ("name", "user__email", "user__phone_number")
    list_filter = ("type",)
    ordering = ("type", "name")

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "type", "amount", "title", "occurred_at", "created_at")
    search_fields = ("title", "note", "user__email", "user__phone_number")
    list_filter = ("type", "occurred_at")
    ordering = ("-occurred_at", "-id")

@admin.register(Debt)
class DebtAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "kind", "person_name", "amount", "is_closed", "created_at")
    search_fields = ("person_name", "description", "user__email", "user__phone_number")
    list_filter = ("kind", "is_closed")
    ordering = ("-id",)
