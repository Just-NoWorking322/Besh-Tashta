from django import forms
from .models import User, UserProfile


class UserRegistrationForm(forms.ModelForm):
    """Форма регистрации пользователя"""
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['email', 'phone_number', 'password', 'first_name', 'last_name']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])  # Хешируем пароль
        if commit:
            user.save()
        return user


class UserProfileForm(forms.ModelForm):
    """Форма редактирования профиля пользователя"""

    class Meta:
        model = UserProfile
        fields = ['bio', 'avatar', 'date_of_birth']
