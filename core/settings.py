from pathlib import Path
from datetime import timedelta
from decouple import AutoConfig

BASE_DIR = Path(__file__).resolve().parent.parent
env = AutoConfig(search_path=BASE_DIR)

PRODUCTION = env("PRODUCTION", default=False, cast=bool)
DEBUG = env("DEBUG", default=(not PRODUCTION), cast=bool)
SECRET_KEY = env("SECRET_KEY", default="dev-secret-key")

def env_list(name: str, default=""):
    raw = env(name, default=default)
    if not raw:
        return []
    return [x.strip() for x in str(raw).split(",") if x.strip()]

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", default="*") if not PRODUCTION else env_list("ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", default="")
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", default="")
CORS_ALLOW_ALL_ORIGINS = (not PRODUCTION)
CORS_ALLOW_CREDENTIALS = True

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "jazzmin",
    "drf_spectacular",
    "rest_framework",
    "corsheaders",
    "django_filters",
    "rest_framework_simplejwt.token_blacklist",
    "channels",
    "apps.users",
    "apps.management",
    "apps.motivation",
    "apps.notifications",	
]

AUTH_USER_MODEL = "users.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",

    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",

    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [],
    "APP_DIRS": True,
    "OPTIONS": {
        "context_processors": [
            "django.template.context_processors.debug",
            "django.template.context_processors.request",
            "django.contrib.auth.context_processors.auth",
            "django.contrib.messages.context_processors.messages",
        ],
    },
}]

JAZZMIN_SETTINGS = {
    "site_title": "Besh-Tashta Admin",
    "site_header": "Besh-Tashta",
    "site_brand": "Besh-Tashta",
    "welcome_sign": "Добро пожаловать в админку",
    "search_model": ["users.User", "management.Transaction", "management.Debt"],
}

ASGI_APPLICATION = "core.asgi.application"
WSGI_APPLICATION = "core.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

LANGUAGE_CODE = "ru"
TIME_ZONE = "Asia/Bishkek"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "static"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
)

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=60),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
}


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SPECTACULAR_SETTINGS = {
    "TITLE": "Besh-Tashta API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,

    "SCHEMA_PATH_PREFIX": r"/api/v1",
    "SCHEMA_PATH_PREFIX_TRIM": True,

    "SERVERS": [
        {"url": "/api/v1", "description": "API v1"}
    ],
    'ENUM_NAME_OVERRIDES': {
        'NotificationTypeEnum': 'apps.notifications.models.Notification.Type', 
        'MotivationTypeEnum': 'apps.motivation.models.MotivationItem.Type',
        'SocialProviderEnum': 'apps.users.models.SocialAccount.PROVIDER_CHOICES',
        'OtpPurposeEnum': 'apps.users.models.OneTimeCode.PURPOSE_CHOICES',
        'TransactionTypeEnum': 'apps.management.models.Transaction.Type',
        'DebtKindEnum': 'apps.management.models.Debt.Kind',
    },
    "APPEND_COMPONENTS": {
        "securitySchemes": {
            "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
        }
    },
    "SECURITY": [{"BearerAuth": []}],
}


EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST")
EMAIL_PORT = env("EMAIL_PORT", cast=int, default=587)

EMAIL_USE_TLS = env("EMAIL_USE_TLS", cast=bool, default=True)
EMAIL_USE_SSL = env("EMAIL_USE_SSL", cast=bool, default=False)

EMAIL_HOST_USER = env("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")

DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default=EMAIL_HOST_USER)

EMAIL_TIMEOUT = env("EMAIL_TIMEOUT", cast=int, default=10)

SOCIAL_AUTH_GOOGLE_CLIENT_ID = env("SOCIAL_AUTH_GOOGLE_CLIENT_ID", default="")
SOCIAL_AUTH_APPLE_CLIENT_ID = env("SOCIAL_AUTH_APPLE_CLIENT_ID", default="")

GOOGLE_CLIENT_ID = SOCIAL_AUTH_GOOGLE_CLIENT_ID
APPLE_CLIENT_ID = SOCIAL_AUTH_APPLE_CLIENT_ID


REDIS_URL = env("REDIS_URL", default="redis://127.0.0.1:6379/0")

# Django cache -> Redis (для аналитики)
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        "KEY_PREFIX": "beshtash",
    }
}
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [REDIS_URL]},
    }
}
FIREBASE_SERVICE_ACCOUNT = env("FIREBASE_SERVICE_ACCOUNT", default="")

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL 
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "Asia/Bishkek"

# from pathlib import Path
# from datetime import timedelta
# from decouple import AutoConfig
# from .env_reader import env

# BASE_DIR = Path(__file__).resolve().parent.parent
# env = AutoConfig(search_path=BASE_DIR)

# PRODUCTION = env("PRODUCTION", default=False, cast=bool)
# DEBUG = env("DEBUG", default=(not PRODUCTION), cast=bool)

# SECRET_KEY = env("SECRET_KEY")


# # ACCOUNT_LOGIN_METHODS = {"email"}
# # ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]

# # -------------------------
# # Helpers for env lists
# # -------------------------
# def env_list(name: str, default=""):
#     raw = env(name, default=default)
#     if not raw:
#         return []
#     return [x.strip() for x in str(raw).split(",") if x.strip()]


# # -------------------------
# # SECURITY / HOSTS
# # -------------------------
# ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", default="*") if not PRODUCTION else env_list("ALLOWED_HOSTS")

# CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", default="")
# CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", default="")

# CORS_ALLOW_ALL_ORIGINS = (not PRODUCTION)  # для дев — можно все
# CORS_ALLOW_CREDENTIALS = True


# # -------------------------
# # APPS
# # -------------------------
# INSTALLED_APPS = [
#     # django
#     "django.contrib.admin",
#     "django.contrib.auth",
#     "django.contrib.contenttypes",
#     "django.contrib.sessions",
#     "django.contrib.messages",
#     "django.contrib.staticfiles",

#     # sites + allauth (если планируешь Google/Apple через web-flow)
#     # "django.contrib.sites",
#     # "allauth",
#     # "allauth.account",
#     # "allauth.socialaccount",
#     # "allauth.socialaccount.providers.google",
#     # "allauth.socialaccount.providers.apple",

#     # admin
#     # "apps.custom_admin",

#     # rest
#     "rest_framework",
#     "corsheaders",
#     "django_filters",

#     # swagger
#     "drf_yasg",

#     # jwt blacklist (если хочешь blacklist/rotate)
#     "rest_framework_simplejwt.token_blacklist",

#     # apps
#     "apps.users",
#     "apps.management",
#     "apps.motivation",
#     # json widget
#     "django_json_widget",
# ]


# # ВАЖНО: кастомный user
# AUTH_USER_MODEL = "users.User"

# SITE_ID = env("SITE_ID", default=1, cast=int)



# # -------------------------
# # MIDDLEWARE
# # -------------------------
# MIDDLEWARE = [
#     "django.middleware.security.SecurityMiddleware",
#     "django.contrib.sessions.middleware.SessionMiddleware",

#     "corsheaders.middleware.CorsMiddleware",
#     "django.middleware.common.CommonMiddleware",
    
#     "django.middleware.csrf.CsrfViewMiddleware",
#     "django.contrib.auth.middleware.AuthenticationMiddleware",
#     # 'allauth.account.middleware.AccountMiddleware',

#     "django.contrib.messages.middleware.MessageMiddleware",

#     "django.middleware.clickjacking.XFrameOptionsMiddleware",
    
# ]


# # -------------------------
# # URLS / TEMPLATES
# # -------------------------
# ROOT_URLCONF = "core.urls"

# TEMPLATES = [
#     {
#         "BACKEND": "django.template.backends.django.DjangoTemplates",
#         "DIRS": [],  # если шаблоны не используешь — оставь так
#         "APP_DIRS": True,
#         "OPTIONS": {
#             "context_processors": [
#                 "django.template.context_processors.debug",
#                 "django.template.context_processors.request",
#                 "django.contrib.auth.context_processors.auth",
#                 "django.contrib.messages.context_processors.messages",
#             ],
#         },
#     },
# ]

# WSGI_APPLICATION = "core.wsgi.application"


# # -------------------------
# # DATABASE
# # -------------------------
# # По умолчанию SQLite, можно заменить на Postgres через env
# DB_ENGINE = env("DB_ENGINE", default="sqlite")
# if DB_ENGINE == "postgres":
#     DATABASES = {
#         "default": {
#             "ENGINE": "django.db.backends.postgresql",
#             "NAME": env("DB_NAME"),
#             "USER": env("DB_USER"),
#             "PASSWORD": env("DB_PASSWORD"),
#             "HOST": env("DB_HOST", default="localhost"),
#             "PORT": env("DB_PORT", default="5432"),
#         }
#     }
# else:
#     DATABASES = {
#         "default": {
#             "ENGINE": "django.db.backends.sqlite3",
#             "NAME": BASE_DIR / "db.sqlite3",
#         }
#     }


# # -------------------------
# # PASSWORD VALIDATORS
# # -------------------------
# AUTH_PASSWORD_VALIDATORS = [
#     {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
#     {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
#     {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
#     {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
# ]


# # -------------------------
# # LANGUAGE / TIME
# # -------------------------
# LANGUAGE_CODE = "ru"
# TIME_ZONE = "Asia/Bishkek"
# USE_I18N = True
# USE_TZ = True


# # -------------------------
# # STATIC / MEDIA
# # -------------------------
# STATIC_URL = "/static/"
# STATIC_ROOT = BASE_DIR / "static"

# MEDIA_URL = "/media/"
# MEDIA_ROOT = BASE_DIR / "media"


# # -------------------------
# # AUTH BACKENDS
# # (ОБЯЗАТЕЛЬНО добавить ModelBackend, иначе админка/permissions страдают)
# # -------------------------
# AUTHENTICATION_BACKENDS = (
#     "django.contrib.auth.backends.ModelBackend",
#     # "allauth.account.auth_backends.AuthenticationBackend",
# )


# # -------------------------
# # ALLAUTH (можно оставить, но для Android чаще делают отдельный flow)
# # # -------------------------
# # ACCOUNT_EMAIL_REQUIRED = True

# # # Для API обычно лучше 'none' или 'optional', чтобы не блокировало регистрацию
# # ACCOUNT_EMAIL_VERIFICATION = env("ACCOUNT_EMAIL_VERIFICATION", default="none")
# # ACCOUNT_AUTHENTICATION_METHOD = "email"
# # LOGIN_REDIRECT_URL = "/"

# # SOCIALACCOUNT_PROVIDERS = {
# #     "google": {
# #         "SCOPE": ["email", "profile"],
# #         "AUTH_PARAMS": {"access_type": "online"},
# #         "OAUTH_PKCE_ENABLED": True,
# #     },
# #     "apple": {"SCOPE": ["email", "name"]},
# # }


# # # -------------------------
# # DRF
# # -------------------------
# REST_FRAMEWORK = {
#     "DEFAULT_AUTHENTICATION_CLASSES": [
#         "rest_framework_simplejwt.authentication.JWTAuthentication",
#     ],
#     "DEFAULT_PERMISSION_CLASSES": [
#         "rest_framework.permissions.IsAuthenticated",
#     ],
#     "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
#     "PAGE_SIZE": 20,
#     "DEFAULT_FILTER_BACKENDS": [
#         "django_filters.rest_framework.DjangoFilterBackend",
#     ],
# }


# # -------------------------
# # SIMPLE JWT
# # (безопасный дефолт для мобилки)
# # -------------------------
# SIMPLE_JWT = {
#     "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
#     "REFRESH_TOKEN_LIFETIME": timedelta(days=60),

#     # если хочешь максимальную безопасность:
#     "ROTATE_REFRESH_TOKENS": True,
#     "BLACKLIST_AFTER_ROTATION": True,

#     "ALGORITHM": "HS256",
#     "SIGNING_KEY": SECRET_KEY,
#     "AUTH_HEADER_TYPES": ("Bearer",),
# }


# # -------------------------
# # EMAIL (если надо)
# # -------------------------
# EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
# EMAIL_USE_TLS = True
# EMAIL_HOST = "smtp.gmail.com"
# EMAIL_PORT = 587
# EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
# EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")


# DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
