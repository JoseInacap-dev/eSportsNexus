from django.contrib import admin

from training.models import TrainingAttendance, TrainingSession


class TrainingAttendanceInline(admin.TabularInline):
    model = TrainingAttendance
    extra = 0


@admin.register(TrainingSession)
class TrainingSessionAdmin(admin.ModelAdmin):
    list_display = ("title", "team", "scheduled_at", "status")
    list_filter = ("status", "team")
    search_fields = ("title", "team__name")
    inlines = [TrainingAttendanceInline]


@admin.register(TrainingAttendance)
class TrainingAttendanceAdmin(admin.ModelAdmin):
    list_display = ("session", "player", "status")
    list_filter = ("status",)
    search_fields = ("player__nickname",)