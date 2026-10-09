from rest_framework import serializers

from staff.models import StaffMember, TeamStaffAssignment


class StaffMemberSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = StaffMember
        fields = [
            "id",
            "user",
            "first_name",
            "last_name",
            "full_name",
            "email",
            "phone",
            "country",
        ]
        read_only_fields = ["id"]


class TeamStaffAssignmentSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source="staff.full_name", read_only=True)
    team_name = serializers.CharField(source="team.name", read_only=True)

    class Meta:
        model = TeamStaffAssignment
        fields = [
            "id",
            "staff",
            "staff_name",
            "team",
            "team_name",
            "role",
            "responsibilities",
            "started_at",
            "ended_at",
        ]
        read_only_fields = ["id"]