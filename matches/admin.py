from django.contrib import admin

from core.admin import NexusDateAdminMixin
from matches.models import (
    Match,
    MatchMap,
    PlayerMatchStat,
    StatDefinition,
    TeamMatchStat,
    Tournament,
    TournamentParticipant,
)


class TournamentParticipantInline(admin.TabularInline):
    model = TournamentParticipant
    extra = 0
    autocomplete_fields = ("team",)


@admin.register(Tournament)
class TournamentAdmin(NexusDateAdminMixin, admin.ModelAdmin):
    list_display = (
        "name",
        "game",
        "format",
        "participants_count",
        "groups_count",
        "start_date",
    )
    list_filter = ("format", "game")
    search_fields = ("name", "game__name")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [TournamentParticipantInline]


@admin.register(TournamentParticipant)
class TournamentParticipantAdmin(admin.ModelAdmin):
    list_display = ("tournament", "team", "group_name", "seed")
    list_filter = ("tournament", "group_name")
    search_fields = ("team__name", "tournament__name")
    autocomplete_fields = ("team", "tournament")


class MatchMapInline(admin.TabularInline):
    model = MatchMap
    extra = 0


class PlayerMatchStatInline(admin.TabularInline):
    model = PlayerMatchStat
    extra = 0


class TeamMatchStatInline(admin.TabularInline):
    model = TeamMatchStat
    extra = 0


@admin.register(Match)
class MatchAdmin(NexusDateAdminMixin, admin.ModelAdmin):
    list_display = (
        "home_team",
        "away_team",
        "tournament",
        "kind",
        "status",
        "scheduled_at",
    )
    list_filter = ("kind", "status", "game")
    search_fields = ("home_team__name", "away_team__name", "tournament__name")
    inlines = [MatchMapInline, PlayerMatchStatInline, TeamMatchStatInline]


@admin.register(MatchMap)
class MatchMapAdmin(admin.ModelAdmin):
    list_display = ("match", "order", "map_name", "home_score", "away_score")


@admin.register(StatDefinition)
class StatDefinitionAdmin(admin.ModelAdmin):
    list_display = ("name", "game", "scope", "code", "is_active")
    list_filter = ("scope", "game")


@admin.register(PlayerMatchStat)
class PlayerMatchStatAdmin(admin.ModelAdmin):
    list_display = ("match", "player", "definition", "value")


@admin.register(TeamMatchStat)
class TeamMatchStatAdmin(admin.ModelAdmin):
    list_display = ("match", "team", "definition", "value")