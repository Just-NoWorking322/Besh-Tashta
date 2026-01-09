from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from apps.users.models import User, UserProfile, UserPrivilege


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "email", "phone_number", "first_name", "last_name", "full_name")

    def get_full_name(self, obj):
        name = f"{obj.first_name} {obj.last_name}".strip()
        return name if name else obj.email


class UserProfileSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = (
            "bio", "avatar", "avatar_url", "date_of_birth",
            "goals_achieved", "saving_days",
            "notifications_enabled", "theme", "language",
        )
        extra_kwargs = {"avatar": {"write_only": True}}

    def get_avatar_url(self, obj):
        request = self.context.get("request")
        if obj.avatar and hasattr(obj.avatar, "url") and request:
            return request.build_absolute_uri(obj.avatar.url)
        return None



class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    phone_number = serializers.CharField(max_length=15)
    password = serializers.CharField(min_length=6, write_only=True)

    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Такой email уже существует")
        return value

    def validate_phone_number(self, value):
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("Такой номер уже существует")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data["email"],
            phone = validated_data["phone_number"].strip(),
            password=validated_data["password"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
        )
        UserProfile.objects.get_or_create(user=user)
        return user


class LoginSerializer(serializers.Serializer):
    login = serializers.CharField()   
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        login = attrs["login"].strip()
        password = attrs["password"]

        user = (
            User.objects.filter(email__iexact=login).first()
            or User.objects.filter(phone_number=login).first()
        )

        if not user or not user.check_password(password):
            raise serializers.ValidationError("Неверный логин или пароль")

        if not user.is_active:
            raise serializers.ValidationError("Пользователь заблокирован")

        refresh = RefreshToken.for_user(user)
        return {"access": str(refresh.access_token), "refresh": str(refresh)}


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(min_length=6, write_only=True)


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def save(self, **kwargs):
        refresh = RefreshToken(self.validated_data["refresh"])
        refresh.blacklist()
        return {}
    

class MeUpdateSerializer(serializers.ModelSerializer):
    # profile fields via source
    bio = serializers.CharField(source="profile.bio", required=False, allow_blank=True, allow_null=True)
    avatar = serializers.ImageField(source="profile.avatar", required=False, allow_null=True)
    date_of_birth = serializers.DateField(source="profile.date_of_birth", required=False, allow_null=True)

    goals_achieved = serializers.IntegerField(source="profile.goals_achieved", required=False)
    saving_days = serializers.IntegerField(source="profile.saving_days", required=False)

    notifications_enabled = serializers.BooleanField(source="profile.notifications_enabled", required=False)
    theme = serializers.CharField(source="profile.theme", required=False)
    language = serializers.CharField(source="profile.language", required=False)

    class Meta:
        model = User
        fields = (
            "first_name", "last_name",
            "bio", "avatar", "date_of_birth",
            "goals_achieved", "saving_days",
            "notifications_enabled", "theme", "language",
        )

    def update(self, instance, validated_data):
        profile_data = validated_data.pop("profile", {})
        profile, _ = UserProfile.objects.get_or_create(user=instance)

        # update user fields
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()

        # update profile fields
        for k, v in profile_data.items():
            setattr(profile, k, v)
        profile.save()

        return instance

