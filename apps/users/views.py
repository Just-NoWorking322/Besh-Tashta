from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from .forms import UserRegistrationForm, UserProfileForm
from django.contrib.auth.decorators import login_required
from django.views.generic import CreateView, UpdateView, ListView, View, TemplateView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Privilege, UserPrivilege

class UserRegisterView(CreateView):
    form_class = UserRegistrationForm
    template_name = 'users/register.html'
    success_url = reverse_lazy('profile')

    def form_valid(self, form):
        """Если форма валидна, сохраняем пользователя и логиним"""
        user = form.save()
        login(self.request, user)
        messages.success(self.request, 'Вы успешно зарегистрированы!')
        return redirect(self.success_url)

class UserProfileView(LoginRequiredMixin, UpdateView):
    form_class = UserProfileForm
    template_name = 'users/profile.html'
    success_url = reverse_lazy('profile')

    def get_object(self, queryset=None):
        """Получаем профиль текущего пользователя"""
        return self.request.user.userprofile

    def form_valid(self, form):
        """Если форма валидна, сохраняем изменения и показываем сообщение"""
        messages.success(self.request, 'Профиль успешно обновлен!')
        return super().form_valid(form)

class PrivilegeListView(LoginRequiredMixin, ListView):
    model = Privilege
    template_name = 'users/privilege_list.html'
    context_object_name = 'privileges'

class BuyPrivilegeView(LoginRequiredMixin, View):
    def post(self, request, privilege_id):
        privilege = Privilege.objects.get(id=privilege_id)

        if UserPrivilege.objects.filter(user=request.user, privilege=privilege).exists():
            messages.warning(request, 'Вы уже купили эту привилегию.')
            return redirect('privilege_list')

        UserPrivilege.objects.create(user=request.user, privilege=privilege)
        messages.success(request, f'Вы успешно купили привилегию "{privilege.name}".')

        return redirect('privilege_list')

class UserProfileWithPrivilegesView(LoginRequiredMixin, TemplateView):
    template_name = 'users/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_privileges'] = UserPrivilege.objects.filter(user=self.request.user)
        return context
    