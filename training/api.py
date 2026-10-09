from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from core.permissions import IsOrganizationManager, user_can_manage_organization
from training.models import TrainingAttendance, TrainingSession
from training.serializers import (
    TrainingAttendanceSerializer,
    TrainingSessionSerializer,
)


class TrainingSessionViewSet(viewsets.ModelViewSet):
    queryset = TrainingSession.objects.select_related(
        "team", "team__organization", "team__game"
    )
    serializer_class = TrainingSessionSerializer
    permission_classes = [IsAuthenticated, IsOrganizationManager]
    search_fields = ["title", "team__name"]
    ordering_fields = ["scheduled_at", "status"]

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
            raise PermissionDenied("No puedes planificar sesiones para ese equipo.")
        serializer.save()


class TrainingAttendanceViewSet(viewsets.ModelViewSet):
    queryset = TrainingAttendance.objects.select_related(
        "session", "session__team", "player"
    )
    serializer_class = TrainingAttendanceSerializer
    permission_classes = [IsAuthenticated, IsOrganizationManager]
    ordering_fields = ["session"]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return queryset
        return queryset.filter(
            session__team__organization__memberships__user=user,
            session__team__organization__memberships__is_active=True,
        ).distinct()

    def perform_create(self, serializer):
        session = serializer.validated_data.get("session")
        if not user_can_manage_organization(
            self.request.user, session.team.organization
        ):
            raise PermissionDenied("No puedes registrar asistencia a esa sesión.")
        serializer.save()