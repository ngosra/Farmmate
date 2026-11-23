import pytest

pytestmark = pytest.mark.django_db

PASSWORD = "Correct-horse-battery-9"


def auth(api, user):
    response = api.post(
        "/api/v1/auth/login/",
        {"identifier": user.email, "password": PASSWORD},
        format="json",
    )
    assert response.status_code == 200
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")


def test_user_cannot_read_another_organization(api, user_a, user_b, org_a, org_b):
    auth(api, user_a)
    listing = api.get("/api/v1/organizations/")
    assert listing.status_code == 200
    ids = {item["id"] for item in listing.data}
    assert str(org_a.id) in ids
    assert str(org_b.id) not in ids

    hidden = api.get(f"/api/v1/organizations/{org_b.id}/")
    assert hidden.status_code == 404

    visible = api.get(f"/api/v1/organizations/{org_a.id}/")
    assert visible.status_code == 200
    assert visible.data["role"] == "org_admin"


def test_other_organization_header_is_not_found(api, user_a, org_b):
    auth(api, user_a)
    response = api.get("/api/v1/auth/me/", HTTP_X_ORGANIZATION_ID=str(org_b.id))
    assert response.status_code == 404


def test_unauthenticated_cannot_list_organizations(api, user_a):
    assert api.get("/api/v1/organizations/").status_code == 401
