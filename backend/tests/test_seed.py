import pytest
from django.core.management import call_command

from certification.models import Certification
from ndvi.models import Observation
from organizations.models import Organization


@pytest.mark.django_db
def test_seed_demo_is_idempotent_and_does_not_invent_evidence(monkeypatch):
    monkeypatch.setenv("FARMMATE_DEMO_PASSWORD", "North-plot-demo-1842")
    call_command("seed_demo")
    call_command("seed_demo")

    assert Organization.objects.filter(slug="demo-cooperative").count() == 1
    certification = Certification.objects.get()
    assert certification.status == Certification.Status.PREPARING
    assert certification.certificate_number == ""
    assert certification.items.filter(state="missing").exists()
    assert Observation.objects.count() == 0
