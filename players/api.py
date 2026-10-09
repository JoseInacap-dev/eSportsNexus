from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from core.permissions import (
    IsOrganizationManager,
    user_can_manage_organization,
    user_manages_any_organization,
)
from players.models import Player, PlayerTeamAssignment
from players.serializers import PlayerSerializer, PlayerTeamAssignmentSerializer


class PlayerViewSet(viewsets.ModelViewSet):
    """CRUD de jugadores. La escritura requiere gestionar alguna organización."""

    queryset = Player.objects.order_by("nickname")
    serializer_class = PlayerSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["nickname", "first_name", "last_name"]
    ordering_fields = ["nickname", "last_name", "created_at"]

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


class PlayerTeamAssignmentViewSet(viewsets.ModelViewSet):
    """Historial de asignaciones de jugadores a equipos."""

    queryset = PlayerTeamAssignment.objects.select_related(
        "player", "team", "team__organization", "competitive_role"
    )
    serializer_class = PlayerTeamAssignmentSerializer
    permission_classes = [IsAuthenticated, IsOrganizationManager]
    ordering_fields = ["joined_at", "left_at"]

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
            raise PermissionDenied("No puedes asignar jugadores a ese equipo.")
        serializer.save()
