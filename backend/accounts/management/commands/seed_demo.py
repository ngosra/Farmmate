import os
from datetime import date
from decimal import Decimal

from django.contrib.auth.password_validation import validate_password
from django.contrib.gis.geos import Polygon
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from accounts.models import User
from certification.models import Certification, Standard
from certification.services import open_certification
from crops.models import Crop, Planting
from farms.geo import hectares_from_polygon
from farms.models import Farm, Field, LandUse
from organizations.models import Farmer, Membership, Organization
from production.models import Activity, Harvest

ORG_SLUG = "demo-cooperative"
ADMIN_EMAIL = "demo-admin@farmmate.example"
FARMER_EMAIL = "farmer@farmmate.example"
FARMER_CODE = "FM-DEMO-001"
MARKER = "seed-demo"


class Command(BaseCommand):
    help = (
        "Create a labeled sample organization, farmer, farm, harvest, and an open "
        "checklist. It does not store satellite readings or a certified decision."
    )

    def handle(self, *args, **options):
        password = os.environ.get("FARMMATE_DEMO_PASSWORD", "")
        organization, _created = Organization.objects.get_or_create(
            slug=ORG_SLUG,
            defaults={"name": "Demo Cooperative"},
        )
        admin = self._user(
            ADMIN_EMAIL,
            password,
            first_name="Demo",
            last_name="Admin",
        )
        farmer_user = self._user(
            FARMER_EMAIL,
            password,
            first_name="Sample",
            last_name="Farmer",
            farmer_id=FARMER_CODE,
        )
        Membership.objects.get_or_create(
            user=admin,
            organization=organization,
            defaults={"role": Membership.Role.ORG_ADMIN},
        )
        Membership.objects.get_or_create(
            user=farmer_user,
            organization=organization,
            defaults={"role": Membership.Role.FARMER},
        )
        farmer, _created = Farmer.objects.get_or_create(
            organization=organization,
            farmer_id=FARMER_CODE,
            defaults={
                "display_name": "Sample Farmer",
                "user": farmer_user,
                "email": FARMER_EMAIL,
                "notes": "Sample profile created by seed_demo.",
            },
        )
        if farmer.user_id is None:
            farmer.user = farmer_user
            farmer.save(update_fields=["user"])

        boundary = Polygon(
            (
                (-1.602, 6.698),
                (-1.598, 6.698),
                (-1.598, 6.702),
                (-1.602, 6.702),
                (-1.602, 6.698),
            ),
            srid=4326,
        )
        area = hectares_from_polygon(boundary)
        farm, _created = Farm.objects.get_or_create(
            organization=organization,
            code="FARM-DEMO",
            defaults={
                "farmer": farmer,
                "name": "Sample plot",
                "latitude": Decimal("6.700000"),
                "longitude": Decimal("-1.600000"),
                "country": "Example",
                "region": "Example region",
                "area_hectares": area,
                "notes": "Sample geometry created by seed_demo. Not a surveyed farm.",
            },
        )
        field, _created = Field.objects.get_or_create(
            farm=farm,
            code="FLD-DEMO",
            defaults={
                "name": "Sample field",
                "boundary": boundary,
                "area_hectares": area,
                "soil_notes": "Sample boundary only.",
            },
        )
        LandUse.objects.get_or_create(
            field=field,
            year=timezone.now().year,
            defaults={"use": "Maize", "notes": MARKER},
        )
        crop, _created = Crop.objects.get_or_create(
            organization=organization,
            name="Maize",
            variety="",
        )
        planting, _created = Planting.objects.get_or_create(
            field=field,
            crop=crop,
            season_year=timezone.now().year,
            defaults={
                "planted_on": date(timezone.now().year, 4, 12),
                "status": Planting.Status.PLANTED,
            },
        )
        if not Harvest.objects.filter(farm=farm, notes=MARKER).exists():
            Harvest.objects.create(
                organization=organization,
                farm=farm,
                field=field,
                planting=planting,
                crop=crop,
                harvested_on=date(timezone.now().year, 8, 20),
                quantity_kg=Decimal("420.000"),
                quality="Sample lot",
                notes=MARKER,
                recorded_by=admin,
            )
        if not Activity.objects.filter(farm=farm, notes=MARKER).exists():
            Activity.objects.create(
                organization=organization,
                farm=farm,
                field=field,
                farmer=farmer,
                actor=farmer_user,
                kind=Activity.Kind.WEEDING,
                occurred_on=timezone.now().date(),
                notes=MARKER,
            )
        standard = Standard.objects.filter(code="EU_ORGANIC", organization__isnull=True).first()
        if standard and not Certification.objects.filter(farm=farm, standard=standard).exists():
            open_certification(
                organization=organization,
                standard=standard,
                actor=admin,
                farmer=farmer,
                farm=farm,
            )
        self.stdout.write(self.style.SUCCESS(f"Sample organization: {organization.name}"))
        self.stdout.write(f"Administrator: {ADMIN_EMAIL}")
        self.stdout.write(f"Farmer: {FARMER_EMAIL} / {FARMER_CODE}")
        self.stdout.write(
            "No satellite observations and no certified decision were stored. "
            "The checklist is preparing, with requirements still missing."
        )

    def _user(self, email, password, **extra):
        user = User.objects.filter(email=email).first()
        if user is None:
            if not password:
                raise CommandError(
                    "Set FARMMATE_DEMO_PASSWORD before the first seed. Nothing was created."
                )
            try:
                validate_password(password)
            except ValidationError as exc:
                raise CommandError(" ".join(exc.messages)) from exc
            return User.objects.create_user(email, password=password, **extra)
        if Membership.objects.filter(user=user).exclude(organization__slug=ORG_SLUG).exists():
            raise CommandError(f"{email} already belongs to another organization.")
        return user
