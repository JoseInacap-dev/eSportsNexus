from django.db import models
from django.db.models import F, Q
from django.utils.translation import gettext_lazy as _


class StaffMember(models.Model):
    """Integrante del staff (entrenador, analista, manager, etc.).

    Al igual que ``Player``, se desacopla del usuario de autenticación mediante
    un vínculo opcional.
    """

    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="staff_profile",
        verbose_name=_("usuario"),
    )
    first_name = models.CharField(_("nombre"), max_length=80)
    last_name = models.CharField(_("apellidos"), max_length=80, blank=True)
    email = models.EmailField(_("correo electrónico"), blank=True)
    phone = models.CharField(_("teléfono"), max_length=32, blank=True)
    country = models.CharField(_("país"), max_length=60, blank=True)
    created_at = models.DateTimeField(_("creado"), auto_now_add=True)
    updated_at = models.DateTimeField(_("actualizado"), auto_now=True)

    class Meta:
        verbose_name = _("integrante del staff")
        verbose_name_plural = _("integrantes del staff")
        ordering = ["last_name", "first_name"]

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self):
        return self.full_name or self.email or f"Staff #{self.pk}"


class TeamStaffAssignment(models.Model):
    """Asignación histórica de un integrante del staff a un equipo."""

    class Role(models.TextChoices):
        HEAD_COACH = "head_coach", _("Entrenador principal")
        ASSISTANT_COACH = "assistant_coach", _("Entrenador asistente")
        ANALYST = "analyst", _("Analista")
        MANAGER = "manager", _("Manager")
        PERFORMANCE = "performance", _("Preparador de rendimiento")
        OTHER = "other", _("Otro")

    staff = models.ForeignKey(
        StaffMember,
        on_delete=models.CASCADE,
        related_name="team_assignments",
        verbose_name=_("integrante del staff"),
    )
    team = models.ForeignKey(
        "organizations.Team",
        on_delete=models.CASCADE,
        related_name="staff_assignments",
        verbose_name=_("equipo"),
    )
    role = models.CharField(_("rol"), max_length=32, choices=Role.choices)
    responsibilities = models.TextField(_("responsabilidades"), blank=True)
    started_at = models.DateField(_("fecha de inicio"))
    ended_at = models.DateField(_("fecha de fin"), null=True, blank=True)
    created_at = models.DateTimeField(_("creado"), auto_now_add=True)
    updated_at = models.DateTimeField(_("actualizado"), auto_now=True)

    class Meta:
        verbose_name = _("asignación de staff")
        verbose_name_plural = _("asignaciones de staff")
        ordering = ["team", "-started_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["staff", "team", "role"],
                condition=Q(ended_at__isnull=True),
                name="unique_open_staff_assignment",
            ),
            models.CheckConstraint(
                condition=Q(ended_at__isnull=True) | Q(ended_at__gte=F("started_at")),
                name="staff_assignment_end_not_before_start",
            ),
        ]
        indexes = [
            models.Index(fields=["team", "role"]),
        ]

    def __str__(self):
        return f"{self.staff} · {self.get_role_display()} → {self.team}"
