from farms.models import Farm, Field
from organizations.models import Farmer, Membership


def scoped_farmers(user, membership):
    queryset = Farmer.objects.filter(organization=membership.organization)
    if membership.role == Membership.Role.FARMER and not user.is_superuser:
        queryset = queryset.filter(user=user)
    return queryset


def scoped_farms(user, membership):
    queryset = Farm.objects.filter(organization=membership.organization).select_related("farmer")
    if membership.role == Membership.Role.FARMER and not user.is_superuser:
        queryset = queryset.filter(farmer__user=user)
    return queryset


def scoped_fields(user, membership):
    return Field.objects.filter(farm__in=scoped_farms(user, membership)).select_related("farm")
