from rest_framework import serializers

from organizations.models import Game, GameRole, Organization, Team


class GameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Game
        fields = ["id", "name", "slug", "short_name", "default_team_size", "is_active"]


class GameRoleSerializer(serializers.ModelSerializer):
    game_name = serializers.CharField(source="game.name", read_only=True)

    class Meta:
        model = GameRole
        fields = ["id", "game", "game_name", "name", "abbreviation", "description"]


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "slug",
            "abbreviation",
            "country",
            "website",
            "is_active",
        ]


class TeamSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    game_name = serializers.CharField(source="game.name", read_only=True)

    class Meta:
        model = Team
        fields = [
            "id",
            "organization",
            "organization_name",
            "game",
            "game_name",
            "name",
            "slug",
            "description",
            "status",
            "founded_date",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
