from rest_framework import serializers

from training.models import TrainingAttendance, TrainingSession


class TrainingSessionSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source="team.name", read_only=True)

    class Meta:
        model = TrainingSession
        fields = [
            "id",
            "team",
            "team_name",
            "title",
            "scheduled_at",
            "duration_minutes",
            "location",
            "objectives",
            "plan",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class TrainingAttendanceSerializer(serializers.ModelSerializer):
    player_nickname = serializers.CharField(source="player.nickname", read_only=True)

    class Meta:
        model = TrainingAttendance
        fields = [
            "id",
            "session",
            "player",
            "player_nickname",
            "status",
            "notes",
        ]
        read_only_fields = ["id"]