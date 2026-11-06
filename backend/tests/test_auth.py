import pytest
from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError

from accounts.models import User
from api.auth import LoginRateThrottle
from organizations.models import Membership

pytestmark = pytest.mark.django_db

PASSWORD = "Correct-horse-battery-9"


def test_login_with_email(api, user_a):
    response = api.post(
        "/api/v1/auth/login/",
        {"identifier": "A@farmmate.test", "password": PASSWORD},
        format="json",
    )
    assert response.status_code == 200
    assert "access" in response.data
    assert "refresh" not in response.data
    cookie = response.cookies["farmmate_refresh"]
    assert cookie["httponly"]
    assert cookie["path"] == "/api/v1/auth/"


def test_login_with_farmer_id(api, user_a):
    response = api.post(
        "/api/v1/auth/login/",
        {"identifier": "fm-001", "password": PASSWORD},
        format="json",
    )
    assert response.status_code == 200
    me = api.get(
        "/api/v1/auth/me/",
        HTTP_AUTHORIZATION=f"Bearer {response.data['access']}",
    )
    assert me.status_code == 200
    assert me.data["email"] == "a@farmmate.test"
    assert me.data["farmer_id"] == "FM-001"
    assert me.data["organization"]["name"] == "Org A"
    assert me.data["organization"]["role"] == Membership.Role.ORG_ADMIN


def test_wrong_password_is_rejected(api, user_a):
    response = api.post(
        "/api/v1/auth/login/",
        {"identifier": "a@farmmate.test", "password": "wrong-password"},
        format="json",
    )
    assert response.status_code == 401
    assert "access" not in response.data


def test_there_is_no_public_register_route(api):
    before = User.objects.count()
    register = api.post(
        "/api/v1/auth/register/",
        {"identifier": "new@farmmate.test", "password": PASSWORD},
        format="json",
    )
    users = api.post(
        "/api/v1/users/",
        {"email": "new@farmmate.test", "password": PASSWORD},
        format="json",
    )
    assert register.status_code == 404
    assert users.status_code == 404
    assert User.objects.count() == before


def test_unauthenticated_me_is_rejected(api):
    assert api.get("/api/v1/auth/me/").status_code == 401


def test_refresh_rotates_and_logout_clears_cookie(api, user_a):
    login = api.post(
        "/api/v1/auth/login/",
        {"identifier": "a@farmmate.test", "password": PASSWORD},
        format="json",
    )
    first_refresh = login.cookies["farmmate_refresh"].value
    refreshed = api.post("/api/v1/auth/refresh/", format="json")
    assert refreshed.status_code == 200
    rotated = refreshed.cookies["farmmate_refresh"].value
    assert rotated != first_refresh

    api.cookies["farmmate_refresh"] = first_refresh
    reused = api.post("/api/v1/auth/refresh/", format="json")
    assert reused.status_code == 401

    api.cookies["farmmate_refresh"] = rotated
    logout = api.post(
        "/api/v1/auth/logout/",
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {refreshed.data['access']}",
    )
    assert logout.status_code == 204


def test_login_is_throttled(api, user_a, monkeypatch):
    cache.clear()
    monkeypatch.setattr(LoginRateThrottle, "get_rate", lambda self: "2/min")
    payload = {"identifier": "a@farmmate.test", "password": "wrong-password"}
    assert api.post("/api/v1/auth/login/", payload, format="json").status_code == 401
    assert api.post("/api/v1/auth/login/", payload, format="json").status_code == 401
    assert api.post("/api/v1/auth/login/", payload, format="json").status_code == 429


def test_mobile_login_returns_refresh_token(api, user_a):
    response = api.post(
        "/api/v1/auth/login/",
        {"identifier": "FM-001", "password": PASSWORD},
        format="json",
        HTTP_X_FARMMATE_CLIENT="mobile",
    )
    assert response.status_code == 200
    assert response.data["refresh"]


def test_farmer_id_is_unique():
    User.objects.create_user(
        email="one@farmmate.test",
        password=PASSWORD,
        farmer_id="FM-9",
    )
    with pytest.raises(IntegrityError):
        User.objects.create_user(
            email="two@farmmate.test",
            password=PASSWORD,
            farmer_id="fm-9",
        )


def test_bootstrap_requires_credentials(monkeypatch):
    monkeypatch.delenv("FARMMATE_BOOTSTRAP_EMAIL", raising=False)
    monkeypatch.delenv("FARMMATE_BOOTSTRAP_PASSWORD", raising=False)
    with pytest.raises(CommandError):
        call_command("bootstrap_dev")


def test_bootstrap_creates_org_admin(monkeypatch):
    monkeypatch.setenv("FARMMATE_BOOTSTRAP_EMAIL", "admin@farmmate.test")
    monkeypatch.setenv("FARMMATE_BOOTSTRAP_PASSWORD", PASSWORD)
    monkeypatch.setenv("FARMMATE_BOOTSTRAP_ORG", "Demo Cooperative")
    call_command("bootstrap_dev")
    user = User.objects.get(email="admin@farmmate.test")
    assert user.is_staff
    membership = user.memberships.get()
    assert membership.organization.name == "Demo Cooperative"
    assert membership.role == Membership.Role.ORG_ADMIN
