from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils.translation import gettext_lazy as _


class Player(models.Model):
    """Perfil de un jugador profesional.

    Se mantiene separado del usuario de Django: un jugador puede existir en la
    base de datos sin cuenta, y la cuenta (``user``) es un vínculo opcional que
    no duplica datos de autenticación.
    """

    class PlayerType(models.TextChoices):
        PLAYER = "player", _("Jugador")
        COACH = "coach", _("Entrenador")
        ANALYST = "analyst", _("Analista")
        MANAGER = "manager", _("Manager")

    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="player_profile",
        verbose_name=_("usuario"),
    )
    player_type = models.CharField(
        _("tipo"),
        max_length=16,
        choices=PlayerType.choices,
        default=PlayerType.PLAYER,
    )
    first_name = models.CharField(_("nombre"), max_length=80)
    last_name = models.CharField(_("apellidos"), max_length=80, blank=True)
    nickname = models.CharField(_("nickname"), max_length=60, unique=True)
    email = models.EmailField(_("correo electrónico"), blank=True)
    phone = models.CharField(_("teléfono"), max_length=32, blank=True)
    birth_date = models.DateField(_("fecha de nacimiento"), null=True, blank=True)
    country = models.CharField(_("país"), max_length=60, blank=True)
    created_at = models.DateTimeField(_("creado"), auto_now_add=True)
    updated_at = models.DateTimeField(_("actualizado"), auto_now=True)

    class Meta:
        verbose_name = _("jugador")
        verbose_name_plural = _("jugadores")
        ordering = ["nickname"]
        indexes = [
            models.Index(fields=["last_name", "first_name"]),
            models.Index(fields=["player_type"]),
        ]

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self):
        return self.nickname

    @property
    def current_assignment(self):
        """Asignación abierta (sin fecha de salida) del jugador, si la hay."""
        return (
            self.team_assignments.filter(left_at__isnull=True)
            .select_related("team", "competitive_role")
            .first()
        )

    @property
    def current_team(self):
        assignment = self.current_assignment
        return assignment.team if assignment else None

    @property
    def current_role(self):
        assignment = self.current_assignment
        return assignment.competitive_role if assignment else None

    @property
    def current_status(self):
        assignment = self.current_assignment
        return assignment.get_status_display() if assignment else None


class PlayerTeamAssignment(models.Model):
    """Asignación histórica de un jugador a un equipo.

    Modelo intermedio explícito que aporta datos propios (fechas, rol
    competitivo, estado). Es la pieza que permite reconstruir la
    plantilla actual e histórica de cada equipo.
    """

    class Status(models.TextChoices):
        ACTIVE = "active", _("Titular")
        BENCH = "bench", _("Suplente")
        INACTIVE = "inactive", _("Inactivo")
        LEFT = "left", _("Baja")

    player = models.ForeignKey(
        Player,
        on_delete=models.CASCADE,
        related_name="team_assignments",
        verbose_name=_("jugador"),
    )
    team = models.ForeignKey(
        "organizations.Team",
        on_delete=models.CASCADE,
        related_name="player_assignments",
        verbose_name=_("equipo"),
    )
    competitive_role = models.ForeignKey(
        "organizations.GameRole",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="player_assignments",
        verbose_name=_("rol competitivo"),
    )
    joined_at = models.DateField(_("fecha de incorporación"))
    left_at = models.DateField(_("fecha de salida"), null=True, blank=True)
    status = models.CharField(
        _("estado"), max_length=16, choices=Status.choices, default=Status.ACTIVE
    )
    is_captain = models.BooleanField(_("capitán"), default=False)
    notes = models.TextField(_("notas"), blank=True)
    created_at = models.DateTimeField(_("creado"), auto_now_add=True)
    updated_at = models.DateTimeField(_("actualizado"), auto_now=True)

    class Meta:
        verbose_name = _("asignación de jugador")
        verbose_name_plural = _("asignaciones de jugadores")
        ordering = ["team", "-joined_at"]
        constraints = [
            # Un jugador solo puede tener una asignación abierta a la vez,
            # es decir, un único equipo activo.
            models.UniqueConstraint(
                fields=["player"],
                condition=Q(left_at__isnull=True),
                name="unique_open_assignment_per_player",
            ),
            # Solo puede haber un capitán activo por equipo.
            models.UniqueConstraint(
                fields=["team"],
                condition=Q(is_captain=True, left_at__isnull=True),
                name="unique_captain_per_team",
            ),
            # La fecha de salida no puede ser anterior a la de incorporación.
            models.CheckConstraint(
                condition=Q(left_at__isnull=True) | Q(left_at__gte=F("joined_at")),
                name="assignment_left_not_before_joined",
            ),
        ]
        indexes = [
            models.Index(fields=["player", "status"]),
            models.Index(fields=["team", "status"]),
        ]

    def clean(self):
        """Validación en capa de aplicación.

        El rol competitivo debe pertenecer al mismo juego que el equipo. Es una
        regla que cruza dos tablas y no puede expresarse con una restricción de
        columna simple, por lo que se valida aquí. Además se comprueba que el
        jugador no tenga ya otra asignación abierta (un solo equipo activo) y que
        el equipo no tenga ya otro capitán activo.
        """
        super().clean()
        if self.competitive_role_id and self.team_id:
            if self.competitive_role.game_id != self.team.game_id:
                raise ValidationError(
                    {
                        "competitive_role": _(
                            "El rol competitivo debe pertenecer al mismo juego que el equipo."
                        )
                    }
                )
        if self.player_id and self.left_at is None:
            open_assignments = type(self).objects.filter(
                player_id=self.player_id, left_at__isnull=True
            )
            if self.pk:
                open_assignments = open_assignments.exclude(pk=self.pk)
            if open_assignments.exists():
                raise ValidationError(
                    {
                        "player": _(
                            "El jugador ya tiene una asignación activa en otro equipo."
                        )
                    }
                )
        if self.team_id and self.is_captain and self.left_at is None:
            captains = type(self).objects.filter(
                team_id=self.team_id, is_captain=True, left_at__isnull=True
            )
            if self.pk:
                captains = captains.exclude(pk=self.pk)
            if captains.exists():
                raise ValidationError(
                    {"is_captain": _("El equipo ya tiene un capitán.")}
                )

    def __str__(self):
        return f"{self.player} → {self.team} ({self.get_status_display()})"
