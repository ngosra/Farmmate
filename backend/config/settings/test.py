import os

os.environ.setdefault(
    "DJANGO_SECRET_KEY",
    "test-only-not-a-secret-key-32-bytes-min",
)
os.environ["DATABASE_URL"] = ""

from .base import *  # noqa: E402,F403
from .base import REST_FRAMEWORK as BASE_REST_FRAMEWORK  # noqa: E402

DEBUG = True
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
REST_FRAMEWORK = {
    **BASE_REST_FRAMEWORK,
    "DEFAULT_THROTTLE_RATES": {"login": "1000/min"},
}
