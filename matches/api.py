from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from core.permissions import IsOrganizationManager, user_can_manage_organization
from matches.models import (
    Match,
    MatchMap,
    PlayerMatchStat,
    StatDefinition,
    TeamMatchStat,
)
from matches.serializers import (
    MatchMapSerializer,
    MatchSerializer,
    PlayerMatchStatSerializer,
    StatDefinitionSerializer,
    TeamMatchStatSerializer,
)


class MatchViewSet(viewsets.ModelViewSet):
    queryset = Match.objects.select_related(
        "game", "home_team", "home_team__organization", "away_team"
    )
    serializer_class = MatchSerializer
    permission_classes = [IsAuthenticated, IsOrganizationManager]
    search_fields = [
        "home_team__name",
        "away_team__name",
        "away_name",
        "tournament_name",
    ]
    ordering_fields = ["scheduled_at", "status"]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return queryset
        return queryset.filter(
            home_team__organization__memberships__user=user,
            home_team__organization__memberships__is_active=True,
        ).distinct()

    def perform_create(self, serializer):
        home_team = serializer.validated_data.get("home_team")
        if not user_can_manage_organization(
            self.request.user, home_team.organization
        ):
            raise PermissionDenied("No puedes registrar partidos para ese equipo.")
        serializer.save()


class MatchMapViewSet(viewsets.ModelViewSet):
    queryset = MatchMap.objects.select_related("match", "match__home_team")
    serializer_class = MatchMapSerializer
    permission_classes = [IsAuthenticated, IsOrganizationManager]
    ordering_fields = ["order"]


class StatDefinitionViewSet(viewsets.ModelViewSet):
    queryset = StatDefinition.objects.select_related("game")
    serializer_class = StatDefinitionSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["name", "code"]
    ordering_fields = ["name", "game"]


class PlayerMatchStatViewSet(viewsets.ModelViewSet):
    queryset = PlayerMatchStat.objects.select_related(
        "match", "player", "definition"
    )
    serializer_class = PlayerMatchStatSerializer
    permission_classes = [IsAuthenticated, IsOrganizationManager]
    ordering_fields = ["value"]


class TeamMatchStatViewSet(viewsets.ModelViewSet):
    queryset = TeamMatchStat.objects.select_related("match", "team", "definition")
    serializer_class = TeamMatchStatSerializer
    permission_classes = [IsAuthenticated, IsOrganizationManager]
    ordering_fields = ["value"]