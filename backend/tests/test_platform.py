from datetime import timedelta
from decimal import Decimal

import pytest
from django.core import mail
from django.utils import timezone

from accounts.models import User
from certification.models import Certification, Requirement, Standard
from certification.services import create_expiry_reminders, readiness
from farms.geo import hectares_from_polygon, polygon_from_geojson
from ndvi.models import Observation
from organizations.models import Farmer, Membership

pytestmark = pytest.mark.django_db

PASSWORD = "Correct-horse-battery-9"
SQUARE = {
    "type": "Polygon",
    "coordinates": [
        [
            [-1.60, 6.70],
            [-1.60, 6.71],
            [-1.59, 6.71],
            [-1.59, 6.70],
            [-1.60, 6.70],
        ]
    ],
}


def auth(api, user, password=PASSWORD):
    response = api.post(
        "/api/v1/auth/login/",
        {"identifier": user.email, "password": password},
        format="json",
    )
    assert response.status_code == 200
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    return response


def test_polygon_area_is_calculated_from_the_ring():
    area = hectares_from_polygon(polygon_from_geojson(SQUARE))
    assert Decimal("100") < area < Decimal("150")


def test_farms_are_isolated_and_area_comes_from_the_boundary(api, user_a, user_b):
    auth(api, user_a)
    farmer_id = user_a.farmer_profiles.get().id
    farm = api.post(
        "/api/v1/farms/",
        {"farmer": str(farmer_id), "name": "Ridge", "latitude": "6.700000", "longitude":
            "-1.600000"},
        format="json",
    )
    assert farm.status_code == 201, farm.data
    created = api.post(
        "/api/v1/fields/",
        {"farm": farm.data["id"], "name": "North", "boundary": SQUARE},
        format="json",
    )
    assert created.status_code == 201, created.data
    expected = hectares_from_polygon(polygon_from_geojson(SQUARE))
    assert Decimal(created.data["area_hectares"]) == expected
    assert created.data["missing_land_use_years"]

    auth(api, user_b)
    hidden = api.get(f"/api/v1/farms/{farm.data['id']}/")
    assert hidden.status_code == 404
    assert api.get("/api/v1/farms/").data["count"] == 0


def test_a_farmer_cannot_read_another_farmers_records(api, user_a, org_a):
    auth(api, user_a)
    own = user_a.farmer_profiles.get()
    other_user = User.objects.create_user(
        email="other-farmer@farmmate.test",
        password=PASSWORD,
        farmer_id="FM-200",
    )
    Membership.objects.create(user=other_user, organization=org_a, role=Membership.Role.FARMER)
    other = Farmer.objects.create(
        organization=org_a,
        user=other_user,
        farmer_id="FM-200",
        display_name="Other Farmer",
    )
    farm = api.post(
        "/api/v1/farms/",
        {"farmer": str(other.id), "name": "Other Farm"},
        format="json",
    )
    assert farm.status_code == 201

    auth(api, other_user)
    listing = api.get("/api/v1/farms/")
    assert listing.data["count"] == 1
    assert listing.data["results"][0]["name"] == "Other Farm"
    hidden = api.get(f"/api/v1/farmers/{own.id}/")
    assert hidden.status_code == 404


def test_readiness_uses_verified_weight_and_is_not_a_fixed_percent(api, user_a, org_a):
    standard = Standard.objects.create(code="TEST_STD", name="Test standard", summary="Test only.")
    light = Requirement.objects.create(standard=standard, code="LIGHT", title="Light record",
        weight=1)
    heavy = Requirement.objects.create(standard=standard, code="HEAVY", title="Heavy record",
        weight=3)
    auth(api, user_a)
    farmer = user_a.farmer_profiles.get()
    opened = api.post(
        "/api/v1/certifications/",
        {"standard_id": str(standard.id), "farmer": str(farmer.id)},
        format="json",
    )
    assert opened.status_code == 201, opened.data
    assert opened.data["readiness"]["readiness_percent"] == 0.0
    assert opened.data["readiness"]["is_official_certification"] is False
    assert "not an official certification" in opened.data["readiness"]["message"]

    items = {row["requirement"]["code"]: row for row in opened.data["items"]}
    verified = api.patch(
        f"/api/v1/compliance-items/{items['HEAVY']['id']}/",
        {"state": "verified"},
        format="json",
    )
    assert verified.status_code == 200, verified.data
    declared = api.patch(
        f"/api/v1/compliance-items/{items['LIGHT']['id']}/",
        {"state": "declared"},
        format="json",
    )
    assert declared.status_code == 200
    score = readiness(Certification.objects.get(pk=opened.data["id"]))
    assert score["readiness_percent"] == 75.0
    assert score["readiness_percent"] != 72
    assert light.weight == 1 and heavy.weight == 3

    officer = User.objects.create_user(email="officer@farmmate.test", password=PASSWORD)
    Membership.objects.create(
        user=officer,
        organization=org_a,
        role=Membership.Role.CERTIFICATION_OFFICER,
    )
    farmer_user = User.objects.create_user(
        email="plain-farmer@farmmate.test",
        password=PASSWORD,
        farmer_id="FM-300",
    )
    Membership.objects.create(user=farmer_user, organization=org_a, role=Membership.Role.FARMER)
    Farmer.objects.create(
        organization=org_a,
        user=farmer_user,
        farmer_id="FM-300",
        display_name="Plain Farmer",
    )
    auth(api, farmer_user)
    denied = api.post(
        f"/api/v1/certifications/{opened.data['id']}/decision/",
        {"status": "certified", "certificate_number": "NO-1"},
        format="json",
    )
    assert denied.status_code == 404

    own = api.post(
        "/api/v1/certifications/",
        {"standard_id": str(standard.id)},
        format="json",
    )
    assert own.status_code == 201
    blocked = api.post(
        f"/api/v1/certifications/{own.data['id']}/decision/",
        {"status": "certified", "certificate_number": "NO-2"},
        format="json",
    )
    assert blocked.status_code == 403

    auth(api, officer)
    decided = api.post(
        f"/api/v1/certifications/{opened.data['id']}/decision/",
        {
            "status": "certified",
            "certificate_number": "CERT-100",
            "issued_on": "2026-01-01",
            "expires_on": (timezone.localdate() + timedelta(days=10)).isoformat(),
        },
        format="json",
    )
    assert decided.status_code == 200, decided.data
    assert decided.data["status"] == "certified"
    assert decided.data["readiness"]["readiness_percent"] == 75.0
    assert decided.data["readiness"]["is_official_certification"] is True
    assert create_expiry_reminders() == 1
    assert create_expiry_reminders() == 0


def test_dashboard_does_not_invent_a_readiness_score(api, user_a):
    auth(api, user_a)
    dashboard = api.get("/api/v1/dashboard/")
    assert dashboard.status_code == 200
    assert dashboard.data["certification"]["readiness_percent"] is None
    assert dashboard.data["certification"]["readiness_percent"] != 72
    assert dashboard.data["ndvi"] == []
    assert dashboard.data["satellite_observations"] == 0


def test_manual_ndvi_is_labeled_and_satellite_refresh_stores_nothing(api, user_a):
    auth(api, user_a)
    farmer = user_a.farmer_profiles.get()
    farm = api.post(
        "/api/v1/farms/",
        {"farmer": str(farmer.id), "name": "Sensor Farm"},
        format="json",
    ).data
    field = api.post(
        "/api/v1/fields/",
        {"farm": farm["id"], "name": "Plot"},
        format="json",
    ).data
    refresh = api.post(f"/api/v1/fields/{field['id']}/satellite-refresh/")
    assert refresh.status_code == 503
    assert refresh.data["stored"] == 0
    assert Observation.objects.count() == 0
    created = api.post(
        "/api/v1/observations/",
        {"field": field["id"], "observed_on": "2026-02-01", "ndvi_mean": "0.4200", "source":
            "satellite"},
        format="json",
    )
    assert created.status_code == 201, created.data
    assert created.data["source"] == "manual"
    assert created.data["provider"] == ""


def test_traceability_mass_balance_and_qr(api, user_a):
    auth(api, user_a)
    farmer = user_a.farmer_profiles.get()
    farm = api.post("/api/v1/farms/", {"farmer": str(farmer.id), "name": "Harvest Farm"},
        format="json").data
    field = api.post("/api/v1/fields/", {"farm": farm["id"], "name": "Block", "boundary":
        SQUARE}, format="json").data
    crop = api.post("/api/v1/crops/", {"name": "Maize"}, format="json")
    assert crop.status_code == 201, crop.data
    harvest = api.post(
        "/api/v1/harvests/",
        {
            "farm": farm["id"],
            "field": field["id"],
            "crop": crop.data["id"],
            "harvested_on": "2026-08-01",
            "quantity_kg": "100.000",
        },
        format="json",
    )
    assert harvest.status_code == 201, harvest.data
    batch = api.post(
        "/api/v1/batches/",
        {
            "product_name": "Maize grain",
            "inputs": [{"harvest": harvest.data["id"], "quantity_kg": "100.000"}],
        },
        format="json",
    )
    assert batch.status_code == 201, batch.data
    assert Decimal(batch.data["balance"]["remaining_kg"]) == Decimal("100.000")
    moved = api.post(
        f"/api/v1/batches/{batch.data['id']}/movements/",
        {"kind": "ship", "quantity_kg": "40.000", "loss_kg": "5.000", "happened_on": "2026-08-02"},
        format="json",
    )
    assert moved.status_code == 201, moved.data
    assert Decimal(moved.data["balance"]["remaining_kg"]) == Decimal("55.000")
    over = api.post(
        f"/api/v1/batches/{batch.data['id']}/movements/",
        {"kind": "ship", "quantity_kg": "60.000", "happened_on": "2026-08-03"},
        format="json",
    )
    assert over.status_code == 400
    qr = api.get(f"/api/v1/batches/{batch.data['id']}/qr/")
    assert qr.status_code == 200
    assert qr["Content-Type"] == "image/png"
    traced = api.get(f"/api/v1/trace/{batch.data['public_code']}/")
    assert traced.status_code == 200
    assert traced.data["verification"]["product_name"] == "Maize grain"


def test_prohibited_input_cannot_be_used(api, user_a):
    auth(api, user_a)
    standard = Standard.objects.create(code="INPUT_STD", name="Input standard")
    product = api.post(
        "/api/v1/inputs/",
        {"name": "Restricted spray", "category": "pesticide", "unit": "L"},
        format="json",
    )
    assert product.status_code == 201, product.data
    approval = api.post(
        "/api/v1/input-approvals/",
        {"product": product.data["id"], "standard": str(standard.id), "status": "prohibited"},
        format="json",
    )
    assert approval.status_code == 201, approval.data
    opened = api.post("/api/v1/certifications/", {"standard_id": str(standard.id)}, format="json")
    assert opened.status_code == 400
    Requirement.objects.create(standard=standard, code="ONE", title="One", weight=1)
    opened = api.post("/api/v1/certifications/", {"standard_id": str(standard.id)}, format="json")
    assert opened.status_code == 201
    received = api.post(
        "/api/v1/stock-movements/",
        {"product": product.data["id"], "kind": "in", "quantity": "5.000", "occurred_on":
            "2026-03-01"},
        format="json",
    )
    assert received.status_code == 201, received.data
    used = api.post(
        "/api/v1/stock-movements/",
        {"product": product.data["id"], "kind": "out", "quantity": "1.000", "occurred_on":
            "2026-03-02"},
        format="json",
    )
    assert used.status_code == 400


def test_assistant_uses_records_and_does_not_invent_farms(api, user_a):
    auth(api, user_a)
    standard = Standard.objects.create(code="ASK_STD", name="Ask standard")
    Requirement.objects.create(
        standard=standard,
        code="MAP",
        title="Mapped field boundary",
        weight=1,
    )
    farmer = user_a.farmer_profiles.get()
    opened = api.post(
        "/api/v1/certifications/",
        {"standard_id": str(standard.id), "farmer": str(farmer.id)},
        format="json",
    )
    assert opened.status_code == 201
    answer = api.post(
        "/api/v1/assistant/",
        {"question": 'What compliance evidence is missing for "Nope Farm"?'},
        format="json",
    )
    assert answer.status_code == 200, answer.data
    assert 'No farm named "Nope Farm" is recorded.' in answer.data["answer"]
    assert "Mapped field boundary" in answer.data["answer"]
    assert answer.data["narrative_status"] == "not_configured"
    assert all(row["kind"] != "recorded" or "Nope Farm" not in row["text"] for row in
        answer.data["statements"])
    kinds = {row["kind"] for row in answer.data["statements"]}
    assert "missing" in kinds


def test_password_reset_rotates_the_password_and_invalidates_refresh(api, user_a):
    login = auth(api, user_a)
    requested = api.post(
        "/api/v1/auth/password-reset/",
        {"email": "nobody@farmmate.test"},
        format="json",
    )
    assert requested.status_code == 200
    assert len(mail.outbox) == 0
    requested = api.post(
        "/api/v1/auth/password-reset/",
        {"email": user_a.email},
        format="json",
    )
    assert requested.status_code == 200
    token = mail.outbox[-1].body.split("Or enter this token: ", 1)[1].split()[0]
    updated = api.post(
        "/api/v1/auth/password-reset/confirm/",
        {"token": token, "password": "Replacement-pass-99"},
        format="json",
    )
    assert updated.status_code == 200, updated.data
    api.credentials()
    api.cookies["farmmate_refresh"] = login.cookies["farmmate_refresh"].value
    reused = api.post("/api/v1/auth/refresh/", format="json")
    assert reused.status_code == 401
    signed = api.post(
        "/api/v1/auth/login/",
        {"identifier": user_a.email, "password": "Replacement-pass-99"},
        format="json",
    )
    assert signed.status_code == 200


def test_member_directory_is_limited_to_organization_admins(api, user_a, user_b):
    auth(api, user_b)
    assert api.get("/api/v1/members/").status_code == 403
    auth(api, user_a)
    created = api.post(
        "/api/v1/members/",
        {
            "email": "field@farmmate.test",
            "password": PASSWORD,
            "role": "field_officer",
            "first_name": "Kofi",
        },
        format="json",
    )
    assert created.status_code == 201, created.data
    assert created.data["role"] == "field_officer"
    listing = api.get("/api/v1/members/")
    emails = {row["email"] for row in listing.data["results"]}
    assert "field@farmmate.test" in emails
    assert "b@farmmate.test" not in emails
