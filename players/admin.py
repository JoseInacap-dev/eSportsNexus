from django.contrib import admin

from core.admin import NexusDateAdminMixin
from players.models import Player, PlayerTeamAssignment


@admin.register(Player)
class PlayerAdmin(NexusDateAdminMixin, admin.ModelAdmin):
    list_display = ("nickname", "full_name", "player_type", "country", "user")
    list_filter = ("player_type",)
    search_fields = ("nickname", "first_name", "last_name")


@admin.register(PlayerTeamAssignment)
class PlayerTeamAssignmentAdmin(NexusDateAdminMixin, admin.ModelAdmin):
    list_display = ("player", "team", "status", "joined_at", "left_at")
    list_filter = ("status", "team")
    search_fields = ("player__nickname", "team__name")