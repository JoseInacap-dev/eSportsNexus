from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from core.permissions import (
    IsOrganizationManager,
    user_can_manage_organization,
    user_manages_any_organization,
)
from staff.models import StaffMember, TeamStaffAssignment
from staff.serializers import StaffMemberSerializer, TeamStaffAssignmentSerializer


class StaffMemberViewSet(viewsets.ModelViewSet):
    """CRUD del staff. La escritura requiere gestionar alguna organización."""

    queryset = StaffMember.objects.order_by("last_name", "first_name")
    serializer_class = StaffMemberSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["first_name", "last_name", "email"]
    ordering_fields = ["last_name"]

    def _require_roster_manager(self):
        if not user_manages_any_organization(self.request.user):
            raise PermissionDenied("Necesitas gestionar una organización.")

    def perform_create(self, serializer):
        self._require_roster_manager()
        serializer.save()

    def perform_update(self, serializer):
        self._require_roster_manager()
        serializer.save()

    def perform_destroy(self, instance):
        self._require_roster_manager()
        instance.delete()


class TeamStaffAssignmentViewSet(viewsets.ModelViewSet):
    """Historial de asignaciones de staff a equipos."""

    queryset = TeamStaffAssignment.objects.select_related(
        "staff", "team", "team__organization"
    )
    serializer_class = TeamStaffAssignmentSerializer
    permission_classes = [IsAuthenticated, IsOrganizationManager]
    ordering_fields = ["started_at", "ended_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return queryset
        return queryset.filter(
            team__organization__memberships__user=user,
            team__organization__memberships__is_active=True,
        ).distinct()

    def perform_create(self, serializer):
        team = serializer.validated_data.get("team")
        if not user_can_manage_organization(self.request.user, team.organization):
            raise PermissionDenied("No puedes asignar staff a ese equipo.")
        serializer.save()