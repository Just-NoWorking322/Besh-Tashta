from django.urls import path
from apps.management import views
from apps.management.views import StatsSummaryView, StatsByCategoryView

urlpatterns = [
    path("dashboard/", views.DashboardView.as_view()),

    path("accounts/", views.AccountListCreateView.as_view()),
    path("accounts/<int:pk>/", views.AccountDetailView.as_view()),

    path("categories/", views.CategoryListCreateView.as_view()),
    path("categories/<int:pk>/", views.CategoryDetailView.as_view()),

    path("transactions/", views.TransactionListCreateView.as_view()),
    path("transactions/<int:pk>/", views.TransactionDetailView.as_view()),

    path("debts/", views.DebtListCreateView.as_view()),
    path("debts/<int:pk>/", views.DebtDetailView.as_view()),
    path("debts/<int:pk>/close/", views.DebtCloseView.as_view()),

    path("stats/summary/", StatsSummaryView.as_view()),
    path("stats/categories/", StatsByCategoryView.as_view()),
]