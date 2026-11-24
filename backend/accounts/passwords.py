import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.mail import send_mail
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from accounts.models import PasswordReset, User

RESET_HOURS = 2


def _hash(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def issue_reset(user: User) -> str:
    now = timezone.now()
    PasswordReset.objects.filter(user=user, used_at__isnull=True).update(used_at=now)
    raw = secrets.token_urlsafe(32)
    PasswordReset.objects.create(
        user=user,
        token_hash=_hash(raw),
        expires_at=now + timedelta(hours=RESET_HOURS),
    )
    link = f"{settings.FRONTEND_URL.rstrip('/')}/reset?token={raw}"
    send_mail(
        subject="Reset your FarmMate password",
        message=(
            "A password reset was requested for your FarmMate account.\n\n"
            f"Open this link within {RESET_HOURS} hours:\n{link}\n\n"
            f"Or enter this token: {raw}\n\n"
            "If you did not ask for this, you can ignore the message."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
    return raw


def consume_reset(raw: str, password: str) -> User:
    token = (raw or "").strip()
    if not token:
        raise ValidationError({"token": "This reset link is invalid or has expired."})
    row = PasswordReset.objects.select_related("user").filter(token_hash=_hash(token)).first()
    if row is None or row.used_at is not None or row.expires_at <= timezone.now():
        raise ValidationError({"token": "This reset link is invalid or has expired."})
    if not row.user.is_active:
        raise ValidationError({"token": "This reset link is invalid or has expired."})
    try:
        validate_password(password, row.user)
    except Exception as exc:
        raise ValidationError({"password": list(getattr(exc, "messages", [str(exc)]))}) from exc
    row.user.set_password(password)
    row.user.save(update_fields=["password"])
    row.used_at = timezone.now()
    row.save(update_fields=["used_at"])
    for outstanding in OutstandingToken.objects.filter(user=row.user):
        BlacklistedToken.objects.get_or_create(token=outstanding)
    return row.user
