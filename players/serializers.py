from rest_framework import serializers

from players.models import Player, PlayerTeamAssignment


class PlayerSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Player
        fields = [
            "id",
            "user",
            "first_name",
            "last_name",
            "full_name",
            "nickname",
            "email",
            "phone",
            "birth_date",
            "country",
        ]
        read_only_fields = ["id"]


class PlayerTeamAssignmentSerializer(serializers.ModelSerializer):
    player_nickname = serializers.CharField(source="player.nickname", read_only=True)
    team_name = serializers.CharField(source="team.name", read_only=True)

    class Meta:
        model = PlayerTeamAssignment
        fields = [
            "id",
            "player",
            "player_nickname",
            "team",
            "team_name",
            "competitive_role",
            "jersey_number",
            "joined_at",
            "left_at",
            "status",
            "is_captain",
            "notes",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        role = attrs.get("competitive_role")
        team = attrs.get("team") or getattr(self.instance, "team", None)
        if role is not None and team is not None and role.game_id != team.game_id:
            raise serializers.ValidationError(
                {"competitive_role": "El rol debe pertenecer al juego del equipo."}
            )
        return attrs
