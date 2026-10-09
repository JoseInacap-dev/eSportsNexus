from django.contrib import admin

from matches.models import (
    Match,
    MatchMap,
    PlayerMatchStat,
    StatDefinition,
    TeamMatchStat,
)


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
class MatchAdmin(admin.ModelAdmin):
    list_display = (
        "home_team",
        "away_team",
        "away_name",
        "kind",
        "status",
        "scheduled_at",
    )
    list_filter = ("kind", "status", "game")
    search_fields = ("home_team__name", "away_team__name", "away_name")
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