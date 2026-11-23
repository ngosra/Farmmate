import os

from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from accounts.models import User
from organizations.models import Membership, Organization


class Command(BaseCommand):
    help = (
        "Create a local organization admin from FARMMATE_BOOTSTRAP_EMAIL "
        "and FARMMATE_BOOTSTRAP_PASSWORD."
    )

    def handle(self, *args, **options):
        email = os.environ.get("FARMMATE_BOOTSTRAP_EMAIL", "").strip().lower()
        password = os.environ.get("FARMMATE_BOOTSTRAP_PASSWORD", "")
        org_name = os.environ.get("FARMMATE_BOOTSTRAP_ORG", "FarmMate").strip() or "FarmMate"
        if not email or not password:
            raise CommandError(
                "Set FARMMATE_BOOTSTRAP_EMAIL and FARMMATE_BOOTSTRAP_PASSWORD. Nothing was created."
            )

        slug = slugify(org_name)[:80] or "farmmate"
        organization, _created = Organization.objects.get_or_create(
            slug=slug,
            defaults={"name": org_name},
        )
        user = User.objects.filter(email=email).first()
        if user is None:
            user = User.objects.create_superuser(email=email, password=password)
            self.stdout.write(self.style.SUCCESS(f"Created admin {email}"))
        else:
            user.set_password(password)
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Updated admin {email}"))

        Membership.objects.get_or_create(
            user=user,
            organization=organization,
            defaults={"role": Membership.Role.ORG_ADMIN},
        )
        self.stdout.write(self.style.SUCCESS(f"Organization: {organization.name}"))
