from django.contrib import admin

from organizations.models import Game, GameRole, Organization, Team


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ("name", "short_name", "default_team_size", "is_active")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "short_name")


@admin.register(GameRole)
class GameRoleAdmin(admin.ModelAdmin):
    list_display = ("name", "game", "abbreviation")
    list_filter = ("game",)
    search_fields = ("name",)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "abbreviation", "country", "is_active")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "abbreviation")


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "game", "status")
    list_filter = ("status", "game", "organization")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)
