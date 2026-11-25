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
        "ENGINE": "django.contrib.gis.db.backends.spatialite",
        "NAME": ":memory:",
    }
}
SPATIALITE_LIBRARY_PATH = os.environ.get(
    "SPATIALITE_LIBRARY_PATH",
    "/usr/lib/x86_64-linux-gnu/mod_spatialite.so",
)
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
CELERY_TASK_ALWAYS_EAGER = True
AI_API_KEY = ""
REST_FRAMEWORK = {
    **BASE_REST_FRAMEWORK,
    "DEFAULT_THROTTLE_RATES": {
        "login": "1000/min",
        "register": "1000/min",
        "password_reset": "1000/min",
    },
}
