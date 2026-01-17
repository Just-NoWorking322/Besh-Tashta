from rest_framework import serializers
from .serializers import TransactionSerializer 

class DashboardResponseSerializer(serializers.Serializer):
    total_balance = serializers.CharField()
    monthly_income = serializers.CharField()
    monthly_expense = serializers.CharField()
    balance = serializers.CharField()
    income_total = serializers.CharField()
    expense_total = serializers.CharField()
    # Вот тут магия против additionalProp:
    debts = serializers.DictField(
        child=serializers.CharField(),
        help_text="Словарь вида {'Имя': 'Сумма'}. Пример: {'Иван': '5000.00'}"
    )
    last_transactions = TransactionSerializer(many=True)
    
class DebtCloseResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()


class StatsSummaryResponseSerializer(serializers.Serializer):
    income_total = serializers.CharField()
    expense_total = serializers.CharField()
    balance = serializers.CharField()


class StatsByCategoryItemSerializer(serializers.Serializer):
    category_id = serializers.UUIDField(allow_null=True)
    category_name = serializers.CharField()
    total = serializers.CharField()
    


class StatsByCategoryResponseSerializer(serializers.Serializer):
    type = serializers.CharField()
    items = StatsByCategoryItemSerializer(many=True)
    
class StatsCategorySerializer(serializers.Serializer):
    category_name = serializers.CharField()
    amount = serializers.CharField()
    percent = serializers.IntegerField()