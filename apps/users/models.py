from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.core.validators import EmailValidator


class UserManager(BaseUserManager):
    """Менеджер для модели User"""
    def create_user(self, email, phone_number, password=None):
        if not email:
            raise ValueError("Email обязателен")
        if not phone_number:
            raise ValueError("Номер телефона обязателен")

        email = self.normalize_email(email)
        user = self.model(email=email, phone_number=phone_number)
        user.set_password(password)  # Устанавливаем пароль в хешированном виде
        user.save(using=self._db)
        return user

    def create_superuser(self, email, phone_number, password=None):
        """Создание суперпользователя"""
        user = self.create_user(email, phone_number, password)
        user.is_admin = True
        user.save(using=self._db)
        return user


class User(AbstractBaseUser):
    """Модель пользователя"""
    email = models.EmailField(unique=True, validators=[EmailValidator()])
    phone_number = models.CharField(max_length=15, unique=True)
    first_name = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)

    # Свойства для управления сессиями
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['phone_number', 'password']

    objects = UserManager()

    def __str__(self):
        return self.email

    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True

    @property
    def is_staff(self):
        return self.is_admin


class UserProfile(models.Model):
    """Профиль пользователя"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    date_of_birth = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Profile of {self.user.email}"


class Privilege(models.Model):
    """Модель привилегий"""
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Цена привилегии
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class UserPrivilege(models.Model):
    """Модель привилегий пользователя"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    privilege = models.ForeignKey(Privilege, on_delete=models.CASCADE)
    purchased_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'privilege')  # Одинаковая привилегия не может быть куплена дважды

    def __str__(self):
        return f"{self.user.email} - {self.privilege.name}"