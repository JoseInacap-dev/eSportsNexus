from django.contrib import admin

from staff.models import StaffMember, TeamStaffAssignment


@admin.register(StaffMember)
class StaffMemberAdmin(admin.ModelAdmin):
    list_display = ("full_name", "email", "country")
    search_fields = ("first_name", "last_name", "email")


@admin.register(TeamStaffAssignment)
class TeamStaffAssignmentAdmin(admin.ModelAdmin):
    list_display = ("staff", "team", "role", "started_at", "ended_at")
    list_filter = ("role", "team")
    search_fields = ("staff__first_name", "staff__last_name", "team__name")