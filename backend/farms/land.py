from django.utils import timezone


def missing_land_use_years(field, year=None):
    current = year or timezone.now().year
    wanted = {current, current - 1, current - 2}
    recorded = set(field.land_uses.values_list("year", flat=True))
    return sorted(wanted - recorded)
