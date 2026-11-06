import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from .base import SECRET_KEY  # noqa: E402

DEBUG = False

_DEV_SECRET = "dev-only-not-a-secret-key-32-bytes-min"
if not os.environ.get("DJANGO_SECRET_KEY") or SECRET_KEY == _DEV_SECRET:
    raise ImproperlyConfigured("Set DJANGO_SECRET_KEY to a private value in production.")

if not os.environ.get("DJANGO_ALLOWED_HOSTS"):
    raise ImproperlyConfigured("Set DJANGO_ALLOWED_HOSTS in production.")

SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_REFERRER_POLICY = "same-origin"
