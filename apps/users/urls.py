from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    path('privileges/', views.privilege_list, name='privilege_list'),
    path('privileges/buy/<int:privilege_id>/', views.buy_privilege, name='buy_privilege'),
]
