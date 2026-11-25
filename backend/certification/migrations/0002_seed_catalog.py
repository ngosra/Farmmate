from django.db import migrations

STARTER_CODES = ("EU_ORGANIC", "EUDR", "USDA_NOP")


def forwards(apps, schema_editor):
    from certification.catalog import sync_catalog

    sync_catalog(
        apps.get_model("certification", "Standard"),
        apps.get_model("certification", "Requirement"),
    )


def backwards(apps, schema_editor):
    apps.get_model("certification", "Standard").objects.filter(code__in=STARTER_CODES).delete()


class Migration(migrations.Migration):
    dependencies = [("certification", "0001_initial")]

    operations = [migrations.RunPython(forwards, backwards)]
