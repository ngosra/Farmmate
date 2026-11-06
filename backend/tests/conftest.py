import pytest
from rest_framework.test import APIClient

from accounts.models import User
from organizations.models import Farmer, Membership, Organization

PASSWORD = "Correct-horse-battery-9"


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def org_a():
    return Organization.objects.create(name="Org A", slug="org-a")


@pytest.fixture
def org_b():
    return Organization.objects.create(name="Org B", slug="org-b")


@pytest.fixture
def user_a(org_a):
    user = User.objects.create_user(
        email="a@farmmate.test",
        password=PASSWORD,
        farmer_id="FM-001",
    )
    Membership.objects.create(user=user, organization=org_a, role=Membership.Role.ORG_ADMIN)
    Farmer.objects.create(
        organization=org_a,
        user=user,
        farmer_id="FM-001",
        display_name="Ada Farmer",
    )
    return user


@pytest.fixture
def user_b(org_b):
    user = User.objects.create_user(email="b@farmmate.test", password=PASSWORD)
    Membership.objects.create(user=user, organization=org_b, role=Membership.Role.MANAGER)
    return user
