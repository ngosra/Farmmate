from django.http import Http404

from organizations.models import Membership, Organization


def organizations_for(user):
    if not getattr(user, "is_authenticated", False):
        return Organization.objects.none()
    return Organization.objects.filter(memberships__user=user).distinct()


def get_membership(user, organization_id) -> Membership:
    membership = (
        Membership.objects.select_related("organization")
        .filter(user=user, organization_id=organization_id)
        .first()
    )
    if membership is None:
        raise Http404
    return membership


def active_membership(user, organization_id=None) -> Membership | None:
    if organization_id:
        return get_membership(user, organization_id)
    return (
        Membership.objects.select_related("organization")
        .filter(user=user)
        .order_by("created_at")
        .first()
    )
