from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from accounts.models import OrganizationMembership, User
from accounts.serializers import (
    OrganizationMembershipSerializer,
    UserSerializer,
)
from core.permissions import IsOrganizationManager


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """Consulta de usuarios (solo lectura)."""

    queryset = User.objects.order_by("username")
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["username", "email", "display_name"]
    ordering_fields = ["username"]


class OrganizationMembershipViewSet(viewsets.ModelViewSet):
    """CRUD de membresías. Requiere rol de gestión en la organización."""

    queryset = OrganizationMembership.objects.select_related("user", "organization")
    serializer_class = OrganizationMembershipSerializer
    permission_classes = [IsAuthenticated, IsOrganizationManager]
    ordering_fields = ["organization", "role"]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return queryset
        return queryset.filter(
            organization__memberships__user=user,
            organization__memberships__is_active=True,
        ).distinct()
