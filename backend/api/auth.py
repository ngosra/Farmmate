from django.conf import settings
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User
from organizations.scoping import active_membership

REFRESH_COOKIE = "farmmate_refresh"
REFRESH_COOKIE_PATH = "/api/v1/auth/"
MOBILE_CLIENT_HEADER = "X-FarmMate-Client"


class LoginRateThrottle(AnonRateThrottle):
    scope = "login"


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


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization_id = request.headers.get("X-Organization-Id") or None
        membership = active_membership(request.user, organization_id)
        organization = None
        if membership is not None:
            organization = {
                "id": str(membership.organization_id),
                "name": membership.organization.name,
                "role": membership.role,
            }
        return Response(
            {
                "id": str(request.user.id),
                "email": request.user.email,
                "farmer_id": request.user.farmer_id,
                "organization": organization,
            }
        )
