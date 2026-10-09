"""
Django settings for ragezine_portal project.
"""

from pathlib import Path
import os
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv
from .database import get_database_handler

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret")
DEBUG = os.getenv("DJANGO_DEBUG", "1") in {"1", "true", "True"}
if not DEBUG and (len(SECRET_KEY) < 50 or len(set(SECRET_KEY)) < 5):
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be a strong production secret.")

# Caddy is the public TLS endpoint. Its forwarded scheme passes through nginx.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https") if not DEBUG else None
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_AGE = 8 * 60 * 60
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

ALLOWED_HOSTS = [
    h.strip()
    for h in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if h.strip()
]

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
] if DEBUG else []
CORS_ALLOW_CREDENTIALS = True
CORS_EXPOSE_HEADERS = ["Content-Disposition"]
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
] if DEBUG else []
CSRF_TRUSTED_ORIGINS.extend(
    origin.strip()
    for origin in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
)

INSTALLED_APPS = [
    "corsheaders",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "rest_framework",
    "submissions",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "ragezine_portal.urls"

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = "ragezine_portal.wsgi.application"

DATABASE_HANDLER = get_database_handler(os.getenv("DJANGO_DB_ENGINE", "sqlite"))
DATABASES = {"default": DATABASE_HANDLER.configuration(BASE_DIR, os.environ)}

# Gunicorn runs multiple workers, so production throttles must share a cache.
REDIS_URL = os.getenv("RAGEZINE_REDIS_URL", "").strip()
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
        }
    }
elif DEBUG:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "ragezine-development",
        }
    }
else:
    raise ImproperlyConfigured("RAGEZINE_REDIS_URL is required when DJANGO_DEBUG=0.")

REST_FRAMEWORK = {
    # nginx is the sole proxy directly in front of Django in docker-compose.
    "NUM_PROXIES": int(os.getenv("RAGEZINE_PROXY_COUNT", "1")),
    "DEFAULT_THROTTLE_RATES": {
        "submission_create": os.getenv("RAGEZINE_SUBMISSION_RATE", "5/hour"),
        "login_ip": os.getenv("RAGEZINE_LOGIN_IP_RATE", "15/minute"),
        "login_username": os.getenv("RAGEZINE_LOGIN_USERNAME_RATE", "8/minute"),
        "staff_export": os.getenv("RAGEZINE_EXPORT_RATE", "20/hour"),
    },
}

SUBMISSION_MAX_FILE_BYTES = int(os.getenv("RAGEZINE_MAX_FILE_MB", "5120")) * 1024 * 1024
SUBMISSION_MAX_TOTAL_FILES_BYTES = int(os.getenv("RAGEZINE_MAX_TOTAL_FILES_MB", "10240")) * 1024 * 1024
SUBMISSION_MAX_TEXT_FILES = 10
SUBMISSION_MAX_VISUAL_FILES = 5
DATA_UPLOAD_MAX_NUMBER_FILES = SUBMISSION_MAX_TEXT_FILES + SUBMISSION_MAX_VISUAL_FILES
DATA_UPLOAD_MAX_NUMBER_FIELDS = 100
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
if SUBMISSION_MAX_FILE_BYTES <= 0 or SUBMISSION_MAX_TOTAL_FILES_BYTES < SUBMISSION_MAX_FILE_BYTES:
    raise ImproperlyConfigured(
        "RAGEZINE_MAX_FILE_MB must be positive and no larger than RAGEZINE_MAX_TOTAL_FILES_MB."
    )

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"
LOGIN_URL = "/login"

default_email_backend = (
    "django.core.mail.backends.console.EmailBackend"
    if DEBUG
    else "django.core.mail.backends.smtp.EmailBackend"
)
EMAIL_BACKEND = os.getenv("DJANGO_EMAIL_BACKEND", default_email_backend)
EMAIL_HOST = os.getenv("DJANGO_EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.getenv("DJANGO_EMAIL_PORT", "25"))
EMAIL_HOST_USER = os.getenv("DJANGO_EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("DJANGO_EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("DJANGO_EMAIL_USE_TLS", "0") in {"1", "true", "True"}
EMAIL_USE_SSL = os.getenv("DJANGO_EMAIL_USE_SSL", "0") in {"1", "true", "True"}
DEFAULT_FROM_EMAIL = os.getenv("SUBMISSION_EMAIL_FROM", "no-reply@example.com")
SUBMISSION_EMAIL_FROM = os.getenv("SUBMISSION_EMAIL_FROM", DEFAULT_FROM_EMAIL)
SUBMISSION_EMAIL_SUBJECT = os.getenv(
    "SUBMISSION_EMAIL_SUBJECT",
    "Thank you for submitting to Rage Zine",
)
SUBMISSION_EMAIL_BODY = os.getenv("SUBMISSION_EMAIL_BODY", "")
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = os.getenv("DJANGO_MEDIA_URL", "/media/")
MEDIA_ROOT = Path(os.getenv("DJANGO_MEDIA_ROOT", BASE_DIR / "media"))

STORAGE_BACKEND = os.getenv("RAGEZINE_STORAGE_BACKEND", "local").lower()

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {
            "location": MEDIA_ROOT,
            "base_url": MEDIA_URL,
        },
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

if STORAGE_BACKEND == "s3":
    AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME", "")
    AWS_S3_ENDPOINT_URL = os.getenv("AWS_S3_ENDPOINT_URL", "")
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME", "")
    AWS_QUERYSTRING_AUTH = os.getenv("AWS_QUERYSTRING_AUTH", "1") in {"1", "true", "True"}
    AWS_DEFAULT_ACL = None

    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": AWS_STORAGE_BUCKET_NAME,
            "endpoint_url": AWS_S3_ENDPOINT_URL or None,
            "region_name": AWS_S3_REGION_NAME or None,
            "access_key": AWS_ACCESS_KEY_ID or None,
            "secret_key": AWS_SECRET_ACCESS_KEY or None,
            "querystring_auth": AWS_QUERYSTRING_AUTH,
            "default_acl": AWS_DEFAULT_ACL,
        },
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
