from rest_framework import serializers

from accounts.models import OrganizationMembership, User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "display_name",
            "first_name",
            "last_name",
            "phone",
            "is_active",
        ]
        read_only_fields = ["id"]


class OrganizationMembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationMembership
        fields = [
            "id",
            "user",
            "organization",
            "role",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
