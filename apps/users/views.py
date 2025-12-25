from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from .forms import UserRegistrationForm, UserProfileForm
from .models import User, UserProfile, Privilege, UserPrivilege
from django.contrib.auth.decorators import login_required


def register(request):
    """Регистрация пользователя"""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Вы успешно зарегистрированы!')
            return redirect('profile')
    else:
        form = UserRegistrationForm()
    return render(request, 'users/register.html', {'form': form})


def profile(request):
    """Профиль пользователя"""
    if request.method == 'POST':
        profile_form = UserProfileForm(request.POST, request.FILES, instance=request.user.userprofile)
        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, 'Профиль успешно обновлен!')
            return redirect('profile')
    else:
        profile_form = UserProfileForm(instance=request.user.userprofile)

    return render(request, 'users/profile.html', {'profile_form': profile_form})

@login_required
def privilege_list(request):
    """Страница с доступными привилегиями для покупки"""
    privileges = Privilege.objects.all()  # Получаем все привилегии
    return render(request, 'users/privilege_list.html', {'privileges': privileges})

@login_required
def buy_privilege(request, privilege_id):
    """Покупка привилегии пользователем"""
    privilege = Privilege.objects.get(id=privilege_id)
    
    if UserPrivilege.objects.filter(user=request.user, privilege=privilege).exists():
        messages.warning(request, 'Вы уже купили эту привилегию.')
        return redirect('privilege_list')
    
    UserPrivilege.objects.create(user=request.user, privilege=privilege)
    messages.success(request, f'Вы успешно купили привилегию "{privilege.name}".')
    
    return redirect('privilege_list')
@login_required
def profile(request):
    """Профиль пользователя"""
    user_privileges = UserPrivilege.objects.filter(user=request.user)  
    return render(request, 'users/profile.html', {'user_privileges': user_privileges})
