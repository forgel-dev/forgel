"""Django settings driven entirely by environment variables.

Placeholders only: never commit real credentials. See .env.example.
"""
from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import unquote, urlparse

BASE_DIR = Path(__file__).resolve().parent.parent


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


SECRET_KEY = env("DJANGO_SECRET_KEY", "change-me-in-production")
DEBUG = env("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = [h for h in env("DJANGO_ALLOWED_HOSTS", "*").split(",") if h]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    # DRF resolves its default UNAUTHENTICATED_USER through this app, so it is
    # required even though the skeleton ships no authentication endpoints.
    "django.contrib.auth",
    "django.contrib.staticfiles",
    "rest_framework",
    "storages",
    "health",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": []},
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


def _database_from_url(url: str) -> dict:
    parsed = urlparse(url)
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(parsed.path.lstrip("/")),
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname or "",
        "PORT": str(parsed.port or ""),
    }


# Database: DATABASE_URL wins, then discrete POSTGRES_* variables, then an
# in-memory SQLite fallback so `manage.py test` runs without a server.
if env("DATABASE_URL"):
    DATABASES = {"default": _database_from_url(env("DATABASE_URL"))}
elif env("POSTGRES_HOST") or env("POSTGRES_DB"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("POSTGRES_DB", "app"),
            "USER": env("POSTGRES_USER", "app"),
            "PASSWORD": env("POSTGRES_PASSWORD", ""),
            "HOST": env("POSTGRES_HOST", "localhost"),
            "PORT": env("POSTGRES_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }

# S3-compatible object storage (MinIO locally). The bucket is only configured
# when S3_BUCKET is set, so test runs never reach out to a storage service.
S3_ENDPOINT = env("S3_ENDPOINT")
S3_BUCKET = env("S3_BUCKET")
S3_ACCESS_KEY = env("S3_ACCESS_KEY")
S3_SECRET_KEY = env("S3_SECRET_KEY")
S3_REGION = env("S3_REGION", "us-east-1")

if S3_BUCKET:
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {
                "bucket_name": S3_BUCKET,
                "endpoint_url": S3_ENDPOINT or None,
                "access_key": S3_ACCESS_KEY or None,
                "secret_key": S3_SECRET_KEY or None,
                "region_name": S3_REGION,
            },
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        },
    }
else:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        },
    }

STATIC_URL = "/static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
}
