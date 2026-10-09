from django.db import models
from django.utils.translation import gettext_lazy as _


class TrainingSession(models.Model):
    """Sesión de entrenamiento planificada para un equipo.

    No se almacena el juego: se obtiene del equipo (``team.game``) para evitar
    duplicar información derivable.
    """

    class Status(models.TextChoices):
        PLANNED = "planned", _("Planificada")
        COMPLETED = "completed", _("Completada")
        CANCELLED = "cancelled", _("Cancelada")

    team = models.ForeignKey(
        "organizations.Team",
        on_delete=models.CASCADE,
        related_name="training_sessions",
        verbose_name=_("equipo"),
    )
    title = models.CharField(_("título"), max_length=150)
    scheduled_at = models.DateTimeField(_("fecha y hora"))
    duration_minutes = models.PositiveSmallIntegerField(
        _("duración (minutos)"), null=True, blank=True
    )
    location = models.CharField(_("ubicación"), max_length=150, blank=True)
    objectives = models.TextField(_("objetivos"), blank=True)
    plan = models.TextField(_("planificación"), blank=True)
    status = models.CharField(
        _("estado"), max_length=16, choices=Status.choices, default=Status.PLANNED
    )
    created_at = models.DateTimeField(_("creado"), auto_now_add=True)
    updated_at = models.DateTimeField(_("actualizado"), auto_now=True)

    class Meta:
        verbose_name = _("sesión de entrenamiento")
        verbose_name_plural = _("sesiones de entrenamiento")
        ordering = ["-scheduled_at"]
        indexes = [
            models.Index(fields=["team", "scheduled_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.title} — {self.team} ({self.scheduled_at:%Y-%m-%d})"

    @property
    def game(self):
        return self.team.game

    @property
    def coach(self):
        return self.team.head_coach


class TrainingAttendance(models.Model):
    """Asistencia de un jugador a una sesión de entrenamiento.

    Modelo intermedio con datos propios (estado de asistencia, notas).
    """

    class Attendance(models.TextChoices):
        PRESENT = "present", _("Presente")
        LATE = "late", _("Tarde")
        ABSENT = "absent", _("Ausente")
        EXCUSED = "excused", _("Justificado")

    session = models.ForeignKey(
        TrainingSession,
        on_delete=models.CASCADE,
        related_name="attendance",
        verbose_name=_("sesión"),
    )
    player = models.ForeignKey(
        "players.Player",
        on_delete=models.CASCADE,
        related_name="training_attendance",
        verbose_name=_("jugador"),
    )
    status = models.CharField(
        _("asistencia"),
        max_length=10,
        choices=Attendance.choices,
        default=Attendance.PRESENT,
    )
    notes = models.CharField(_("notas"), max_length=255, blank=True)
    created_at = models.DateTimeField(_("creado"), auto_now_add=True)
    updated_at = models.DateTimeField(_("actualizado"), auto_now=True)

    class Meta:
        verbose_name = _("asistencia a entrenamiento")
        verbose_name_plural = _("asistencias a entrenamiento")
        ordering = ["session", "player"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "player"],
                name="unique_attendance_per_session",
            )
        ]

    def __str__(self):
        return f"{self.player} · {self.session} ({self.get_status_display()})"
