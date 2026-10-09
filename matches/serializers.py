from rest_framework import serializers

from matches.models import (
    Match,
    MatchMap,
    PlayerMatchStat,
    StatDefinition,
    TeamMatchStat,
)


class StatDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatDefinition
        fields = [
            "id",
            "game",
            "scope",
            "code",
            "name",
            "unit",
            "aggregation",
            "higher_is_better",
            "is_active",
        ]
        read_only_fields = ["id"]


class MatchSerializer(serializers.ModelSerializer):
    game_name = serializers.CharField(source="game.name", read_only=True)
    home_team_name = serializers.CharField(source="home_team.name", read_only=True)
    away_team_name = serializers.CharField(source="away_team.name", read_only=True)
    opponent = serializers.SerializerMethodField()

    class Meta:
        model = Match
        fields = [
            "id",
            "game",
            "game_name",
            "home_team",
            "home_team_name",
            "away_team",
            "away_team_name",
            "away_name",
            "opponent",
            "kind",
            "status",
            "scheduled_at",
            "tournament_name",
            "best_of",
            "home_score",
            "away_score",
            "notes",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_opponent(self, obj):
        return obj.away_team.name if obj.away_team_id else obj.away_name


class MatchMapSerializer(serializers.ModelSerializer):
    class Meta:
        model = MatchMap
        fields = [
            "id",
            "match",
            "order",
            "map_name",
            "home_score",
            "away_score",
            "outcome",
        ]
        read_only_fields = ["id"]


class PlayerMatchStatSerializer(serializers.ModelSerializer):
    player_nickname = serializers.CharField(source="player.nickname", read_only=True)
    definition_name = serializers.CharField(source="definition.name", read_only=True)

    class Meta:
        model = PlayerMatchStat
        fields = [
            "id",
            "match",
            "player",
            "player_nickname",
            "definition",
            "definition_name",
            "value",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        definition = attrs.get("definition") or getattr(self.instance, "definition", None)
        match = attrs.get("match") or getattr(self.instance, "match", None)
        if definition is None or match is None:
            return attrs
        if definition.scope != StatDefinition.Scope.PLAYER:
            raise serializers.ValidationError(
                {"definition": "La métrica debe ser de alcance 'jugador'."}
            )
        if definition.game_id != match.game_id:
            raise serializers.ValidationError(
                {"definition": "La métrica debe pertenecer al juego del partido."}
            )
        return attrs


class TeamMatchStatSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source="team.name", read_only=True)
    definition_name = serializers.CharField(source="definition.name", read_only=True)

    class Meta:
        model = TeamMatchStat
        fields = [
            "id",
            "match",
            "team",
            "team_name",
            "definition",
            "definition_name",
            "value",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        definition = attrs.get("definition") or getattr(self.instance, "definition", None)
        match = attrs.get("match") or getattr(self.instance, "match", None)
        if definition is None or match is None:
            return attrs
        if definition.scope != StatDefinition.Scope.TEAM:
            raise serializers.ValidationError(
                {"definition": "La métrica debe ser de alcance 'equipo'."}
            )
        if definition.game_id != match.game_id:
            raise serializers.ValidationError(
                {"definition": "La métrica debe pertenecer al juego del partido."}
            )
        team = attrs.get("team") or getattr(self.instance, "team", None)
        if team is not None and team not in (match.home_team, match.away_team):
            raise serializers.ValidationError(
                {"team": "El equipo no participa en este partido."}
            )
        return attrs