from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User
from accounts.passwords import consume_reset, issue_reset
from organizations.models import Membership, Organization
from organizations.scoping import active_membership

REFRESH_COOKIE = "farmmate_refresh"
REFRESH_COOKIE_PATH = "/api/v1/auth/"
MOBILE_CLIENT_HEADER = "X-FarmMate-Client"


class LoginRateThrottle(AnonRateThrottle):
    scope = "login"


class RegisterRateThrottle(AnonRateThrottle):
    scope = "register"


class PasswordResetRateThrottle(AnonRateThrottle):
    scope = "password_reset"


def authenticate_identifier(identifier: str, password: str) -> User | None:
    ident = identifier.strip()
    if not ident or not password:
        return None
    user = User.objects.filter(email__iexact=ident).first()
    if user is None:
        user = User.objects.filter(farmer_id__iexact=ident.upper()).first()
    if user is None:
        User().set_password(password)
        return None
    if not user.is_active or not user.check_password(password):
        return None
    return user


def set_refresh_cookie(response, token: str) -> None:
    response.set_cookie(
        REFRESH_COOKIE,
        token,
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        httponly=True,
        secure=not settings.DEBUG,
        samesite="Lax",
        path=REFRESH_COOKIE_PATH,
    )


def is_mobile(request) -> bool:
    return request.headers.get(MOBILE_CLIENT_HEADER) == "mobile"


def issue_tokens(user: User, request):
    refresh = RefreshToken.for_user(user)
    body = {"access": str(refresh.access_token)}
    if is_mobile(request):
        body["refresh"] = str(refresh)
    response = Response(body)
    set_refresh_cookie(response, str(refresh))
    return response


class LoginView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        identifier = str(request.data.get("identifier") or "")
        password = str(request.data.get("password") or "")
        user = authenticate_identifier(identifier, password)
        if user is None:
            return Response({"detail": "Invalid identifier or password."}, status=401)
        from organizations.models import AuditLog

        membership = user.memberships.select_related("organization").order_by("created_at").first()
        AuditLog.objects.create(
            organization=membership.organization if membership else None,
            actor=user,
            action="login",
            entity_type="User",
            entity_id=str(user.id),
            summary=f"Signed in {user.email}",
        )
        return issue_tokens(user, request)


class RefreshView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]

    def post(self, request):
        raw = request.COOKIES.get(REFRESH_COOKIE)
        if not raw and is_mobile(request):
            raw = request.data.get("refresh")
        if not raw:
            return Response({"detail": "Refresh token missing."}, status=401)
        try:
            old = RefreshToken(raw)
            user_id = old.get(settings.SIMPLE_JWT["USER_ID_CLAIM"])
            old.blacklist()
        except TokenError:
            return Response({"detail": "Refresh token invalid."}, status=401)
        user = User.objects.filter(pk=user_id, is_active=True).first()
        if user is None:
            return Response({"detail": "Refresh token invalid."}, status=401)
        return issue_tokens(user, request)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        raw = request.COOKIES.get(REFRESH_COOKIE) or request.data.get("refresh")
        if raw:
            try:
                RefreshToken(raw).blacklist()
            except TokenError:
                pass
        response = Response(status=204)
        response.delete_cookie(REFRESH_COOKIE, path=REFRESH_COOKIE_PATH)
        return response


def profile_payload(user, membership):
    organization = None
    if membership is not None:
        organization = {
            "id": str(membership.organization_id),
            "name": membership.organization.name,
            "role": membership.role,
        }
    memberships = [
        {
            "id": str(row.organization_id),
            "name": row.organization.name,
            "role": row.role,
        }
        for row in user.memberships.select_related("organization").order_by("created_at")
    ]
    return {
        "id": str(user.id),
        "email": user.email,
        "farmer_id": user.farmer_id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "phone": user.phone,
        "organization": organization,
        "organizations": memberships,
    }


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization_id = request.headers.get("X-Organization-Id") or None
        membership = active_membership(request.user, organization_id)
        return Response(profile_payload(request.user, membership))

    def patch(self, request):
        user = request.user
        limits = {"first_name": 80, "last_name": 80, "phone": 40}
        for field, limit in limits.items():
            if field in request.data:
                setattr(user, field, str(request.data.get(field) or "")[:limit])
        user.save()
        organization_id = request.headers.get("X-Organization-Id") or None
        membership = active_membership(user, organization_id)
        return Response(profile_payload(user, membership))


class RegisterSerializer(serializers.Serializer):
    organization_name = serializers.CharField(max_length=200)
    email = serializers.EmailField()
    password = serializers.CharField()
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)

    def validate_organization_name(self, value):
        name = value.strip()
        if not name:
            raise serializers.ValidationError("Enter the organization name.")
        return name

    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return email

    def validate_password(self, value):
        validate_password(value)
        return value


class RegisterView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [RegisterRateThrottle]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        with transaction.atomic():
            organization = Organization.objects.create(name=data["organization_name"])
            user = User.objects.create_user(
                email=data["email"],
                password=data["password"],
                first_name=data.get("first_name", ""),
                last_name=data.get("last_name", ""),
            )
            Membership.objects.create(
                user=user,
                organization=organization,
                role=Membership.Role.ORG_ADMIN,
            )
        return issue_tokens(user, request)


class PasswordResetRequestView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetRateThrottle]

    def post(self, request):
        email = str(request.data.get("email") or "").strip().lower()
        user = User.objects.filter(email=email, is_active=True).first()
        if user is not None:
            issue_reset(user)
        return Response(
            {"detail": "If an account exists for that email, a reset message has been sent."}
        )


class PasswordResetConfirmView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]

    def post(self, request):
        consume_reset(
            str(request.data.get("token") or ""),
            str(request.data.get("password") or ""),
        )
        return Response({"detail": "Password updated."})


class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        current = str(request.data.get("current_password") or "")
        new_password = str(request.data.get("password") or "")
        if not request.user.check_password(current):
            raise ValidationError({"current_password": "Current password is wrong."})
        try:
            validate_password(new_password, request.user)
        except Exception as exc:
            raise ValidationError(
                {"password": list(getattr(exc, "messages", [str(exc)]))}
            ) from exc
        request.user.set_password(new_password)
        request.user.save(update_fields=["password"])
        return Response({"detail": "Password updated."})
