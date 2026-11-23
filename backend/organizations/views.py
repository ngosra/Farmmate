from rest_framework.generics import ListAPIView, RetrieveAPIView

from organizations.scoping import organizations_for
from organizations.serializers import OrganizationSerializer


class OrganizationListView(ListAPIView):
    serializer_class = OrganizationSerializer

    def get_queryset(self):
        return organizations_for(self.request.user).order_by("name")


class OrganizationDetailView(RetrieveAPIView):
    serializer_class = OrganizationSerializer

    def get_queryset(self):
        return organizations_for(self.request.user)
