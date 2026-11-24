from django.db.models import ProtectedError
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.viewsets import ModelViewSet

from api.audit import record
from api.pagination import DefaultPagination
from organizations.models import Membership
from organizations.scoping import active_membership


def membership_of(request):
    if getattr(request, "_fm_membership_set", False):
        return request._fm_membership
    org_id = request.headers.get("X-Organization-Id") or None
    found = active_membership(request.user, org_id)
    request._fm_membership = found
    request._fm_membership_set = True
    return found


def require_membership(request):
    found = membership_of(request)
    if found is None:
        raise PermissionDenied("You are not a member of an organization.")
    return found


def allow(request, roles):
    member = require_membership(request)
    if request.user.is_superuser or member.role in roles:
        return member
    raise PermissionDenied("Your role cannot change these records.")


class OrgViewSet(ModelViewSet):
    """Organization-scoped records. Farmers only see rows tied to their user."""

    pagination_class = DefaultPagination
    write_roles: set[str] = set()
    org_field = "organization"
    org_lookup = "organization"
    farmer_lookup = None
    search_fields: tuple[str, ...] = ()
    stamp_user = None

    def get_membership(self):
        return require_membership(self.request)

    def get_queryset(self):
        member = self.get_membership()
        queryset = super().get_queryset()
        if self.org_lookup:
            queryset = queryset.filter(**{f"{self.org_lookup}_id": member.organization_id})
        if (
            self.farmer_lookup
            and member.role == Membership.Role.FARMER
            and not self.request.user.is_superuser
        ):
            queryset = queryset.filter(**{self.farmer_lookup: self.request.user})
        term = (self.request.query_params.get("search") or "").strip()
        if term and self.search_fields:
            from django.db.models import Q

            query = Q()
            for field in self.search_fields:
                query |= Q(**{f"{field}__icontains": term})
            queryset = queryset.filter(query)
        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.request.user.is_authenticated:
            context["membership"] = membership_of(self.request)
        return context

    def _extras(self, member):
        extras = {}
        if self.org_field:
            extras[self.org_field] = member.organization
        if self.stamp_user:
            extras[self.stamp_user] = self.request.user
        return extras

    def perform_create(self, serializer):
        member = allow(self.request, self.write_roles)
        instance = serializer.save(**self._extras(member))
        record(self.request, "create", instance, f"Created {instance}")
        return instance

    def perform_update(self, serializer):
        allow(self.request, self.write_roles)
        instance = serializer.save()
        record(self.request, "update", instance, f"Updated {instance}")
        return instance

    def perform_destroy(self, instance):
        allow(self.request, self.write_roles)
        record(self.request, "delete", instance, f"Deleted {instance}")
        try:
            instance.delete()
        except ProtectedError as exc:
            raise ValidationError(
                {"detail": "This record is still used by other records."}
            ) from exc
