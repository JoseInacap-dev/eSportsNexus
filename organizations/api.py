from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from core.permissions import IsOrganizationManager, user_can_manage_organization
from organizations.models import Game, GameRole, Organization, Team
from organizations.serializers import (
    GameRoleSerializer,
    GameSerializer,
    OrganizationSerializer,
    TeamSerializer,
)


class GameViewSet(viewsets.ModelViewSet):
    queryset = Game.objects.order_by("name")
    serializer_class = GameSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["name", "short_name"]
    ordering_fields = ["name"]


class GameRoleViewSet(viewsets.ModelViewSet):
    queryset = GameRole.objects.select_related("game")
    serializer_class = GameRoleSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["name"]
    ordering_fields = ["game", "name"]


class OrganizationViewSet(viewsets.ModelViewSet):
    queryset = Organization.objects.order_by("name")
    serializer_class = OrganizationSerializer
    permission_classes = [IsAuthenticated, IsOrganizationManager]
    search_fields = ["name", "abbreviation", "country"]
    ordering_fields = ["name"]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return queryset
        return queryset.filter(
            memberships__user=user, memberships__is_active=True
        ).distinct()

    def perform_create(self, serializer):
        if not self.request.user.is_superuser:
            raise PermissionDenied(
                "Solo un administrador global puede crear organizaciones."
            )
        serializer.save()


class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.select_related("organization", "game")
    serializer_class = TeamSerializer
    permission_classes = [IsAuthenticated, IsOrganizationManager]
    search_fields = ["name", "organization__name", "game__name"]
    ordering_fields = ["name", "organization", "game"]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return queryset
        return queryset.filter(
            organization__memberships__user=user,
            organization__memberships__is_active=True,
        ).distinct()

    def perform_create(self, serializer):
        organization = serializer.validated_data.get("organization")
        if not user_can_manage_organization(self.request.user, organization):
            raise PermissionDenied(
                "No puedes crear equipos en esa organización."
            )
        serializer.save()

    def perform_update(self, serializer):
        organization = serializer.validated_data.get(
            "organization", serializer.instance.organization
        )
        if not user_can_manage_organization(self.request.user, organization):
            raise PermissionDenied(
                "No puedes mover el equipo a esa organización."
            )
        serializer.save()
