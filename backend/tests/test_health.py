import pytest
from django.conf import settings

from config.settings.base import database_from_url

pytestmark = pytest.mark.django_db


def test_health_returns_ok(api):
    response = api.get("/api/v1/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_gis_app_is_installed():
    assert "django.contrib.gis" in settings.INSTALLED_APPS


def test_postgis_url_selects_gis_engine():
    config = database_from_url("postgis://farmmate:local-dev-only@localhost:5432/farmmate")
    assert config["ENGINE"] == "django.contrib.gis.db.backends.postgis"
    assert config["NAME"] == "farmmate"
    assert config["USER"] == "farmmate"
    assert config["HOST"] == "localhost"
    assert config["PORT"] == "5432"
