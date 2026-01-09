from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from apps.users.views import (
    RegisterView, LoginView, MeView,
    MyPrivilegesView, BuyPrivilegeView, ChangePasswordView, LogoutView,
    PrivilegeListView
)
from apps.users.social_auth import GoogleAuthView, AppleAuthView, SocialCompleteView
from apps.users.password_reset import PasswordResetRequestView, PasswordResetConfirmView


urlpatterns = [
    path("auth/register/", RegisterView.as_view()),
    path("auth/login/", LoginView.as_view()),
    path("auth/refresh/", TokenRefreshView.as_view()),
    path("auth/logout/", LogoutView.as_view()),
    path("me/", MeView.as_view()),
    path("me/privileges/", MyPrivilegesView.as_view()),
    path("privileges/", PrivilegeListView.as_view()),
    path("privileges/<int:privilege_id>/buy/", BuyPrivilegeView.as_view()),
    
    path("me/change-password/", ChangePasswordView.as_view()),
   
    path("auth/password/reset/request/", PasswordResetRequestView.as_view()),
    path("auth/password/reset/confirm/", PasswordResetConfirmView.as_view()),
    path("auth/social/complete/", SocialCompleteView.as_view()),

    path("auth/google/", GoogleAuthView.as_view()),
    path("auth/apple/", AppleAuthView.as_view()),
]
