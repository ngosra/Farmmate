import os
from datetime import timedelta
from pathlib import Path
from urllib.parse import unquote, urlparse

from corsheaders.defaults import default_headers

BASE_DIR = Path(__file__).resolve().parents[2]


def env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value


def env_bool(name: str, default: bool = False) -> bool:
    raw = env(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


def database_from_url(url: str) -> dict:
    if not url or url.startswith("sqlite"):
        name: str | Path = BASE_DIR / "db.sqlite3"
        if url in {"sqlite://:memory:", "sqlite:///:memory:"}:
            name = ":memory:"
        elif url.startswith("sqlite:///"):
            path = url[len("sqlite:///") :]
            if path and path != ":memory:":
                name = path
        return {"ENGINE": "django.db.backends.sqlite3", "NAME": name}

    parsed = urlparse(url)
    if parsed.scheme not in {"postgres", "postgresql", "postgis"}:
        raise ValueError(f"Unsupported DATABASE_URL scheme: {parsed.scheme}")
    return {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": unquote(parsed.path.lstrip("/")),
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname or "",
        "PORT": str(parsed.port or "5432"),
    }


SECRET_KEY = env("DJANGO_SECRET_KEY", "dev-only-not-a-secret-key-32-bytes-min")
DEBUG = env_bool("DJANGO_DEBUG", False)
ALLOWED_HOSTS = [
    host.strip()
    for host in (env("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1") or "").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",
    "rest_framework",
    "corsheaders",
    "rest_framework_simplejwt.token_blacklist",
    "accounts",
    "organizations",
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

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {"default": database_from_url(env("DATABASE_URL", "") or "")}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "login": "10/min",
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in (
        env("CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173") or ""
    ).split(",")
    if origin.strip()
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = (*default_headers, "x-organization-id", "x-farmmate-client")
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "farmmate",
    }
}
