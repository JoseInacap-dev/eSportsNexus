from rest_framework import serializers

from players.models import Player, PlayerTeamAssignment


class PlayerSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Player
        fields = [
            "id",
            "player_type",
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
        player = attrs.get("player") or getattr(self.instance, "player", None)
        left_at = attrs.get("left_at", getattr(self.instance, "left_at", None))
        if player is not None and left_at is None:
            open_assignments = PlayerTeamAssignment.objects.filter(
                player=player, left_at__isnull=True
            )
            if self.instance is not None:
                open_assignments = open_assignments.exclude(pk=self.instance.pk)
            if open_assignments.exists():
                raise serializers.ValidationError(
                    {
                        "player": "El jugador ya tiene una asignación activa en otro equipo."
                    }
                )
        is_captain = attrs.get(
            "is_captain", getattr(self.instance, "is_captain", False)
        )
        if is_captain and left_at is None and team is not None:
            captains = PlayerTeamAssignment.objects.filter(
                team=team, is_captain=True, left_at__isnull=True
            )
            if self.instance is not None:
                captains = captains.exclude(pk=self.instance.pk)
            if captains.exists():
                raise serializers.ValidationError(
                    {"is_captain": "El equipo ya tiene un capitán."}
                )
        return attrs
