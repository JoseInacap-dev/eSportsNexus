from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class Game(models.Model):
    """Juego competitivo (Valorant, League of Legends, CS, etc.).

    Se modela como entidad propia porque cada título define sus propios roles,
    métricas estadísticas y tamaño de plantilla; no pueden asumirse comunes.
    """

    name = models.CharField(_("nombre"), max_length=100, unique=True)
    slug = models.SlugField(_("slug"), max_length=100, unique=True)
    short_name = models.CharField(_("abreviatura"), max_length=20, blank=True)
    default_team_size = models.PositiveSmallIntegerField(
        _("jugadores por equipo"),
        default=5,
        validators=[MinValueValidator(1)],
    )
    is_active = models.BooleanField(_("activo"), default=True)
    created_at = models.DateTimeField(_("creado"), auto_now_add=True)
    updated_at = models.DateTimeField(_("actualizado"), auto_now=True)

    class Meta:
        verbose_name = _("juego competitivo")
        verbose_name_plural = _("juegos competitivos")
        ordering = ["name"]

    def __str__(self):
        return self.name


class GameRole(models.Model):
    """Rol competitivo dentro de un juego concreto.

    Ejemplos: "Duelist"/"Controller" en Valorant, "Top"/"Jungle" en LoL.
    Definirlos como entidad por juego evita asumir que todos los títulos
    comparten los mismos roles.
    """

    game = models.ForeignKey(
        Game,
        on_delete=models.CASCADE,
        related_name="roles",
        verbose_name=_("juego"),
    )
    name = models.CharField(_("nombre"), max_length=60)
    abbreviation = models.CharField(_("abreviatura"), max_length=10, blank=True)
    description = models.TextField(_("descripción"), blank=True)
    created_at = models.DateTimeField(_("creado"), auto_now_add=True)
    updated_at = models.DateTimeField(_("actualizado"), auto_now=True)

    class Meta:
        verbose_name = _("rol de juego")
        verbose_name_plural = _("roles de juego")
        ordering = ["game", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["game", "name"], name="unique_game_role_name"
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.game.short_name or self.game.name})"


class Organization(models.Model):
    """Organización de esports propietaria de uno o varios equipos."""

    name = models.CharField(_("nombre"), max_length=150, unique=True)
    slug = models.SlugField(_("slug"), max_length=150, unique=True)
    abbreviation = models.CharField(_("abreviatura"), max_length=20, blank=True)
    country = models.CharField(_("país"), max_length=60, blank=True)
    website = models.URLField(_("sitio web"), blank=True)
    description = models.TextField(_("descripción"), blank=True)
    founded_date = models.DateField(_("fecha de fundación"), null=True, blank=True)
    is_active = models.BooleanField(_("activa"), default=True)
    created_at = models.DateTimeField(_("creado"), auto_now_add=True)
    updated_at = models.DateTimeField(_("actualizado"), auto_now=True)

    class Meta:
        verbose_name = _("organización")
        verbose_name_plural = _("organizaciones")
        ordering = ["name"]

    def __str__(self):
        return self.name


class Team(models.Model):
    """Equipo competitivo perteneciente a una organización y a un juego."""

    class Status(models.TextChoices):
        ACTIVE = "active", _("Activo")
        PAUSED = "paused", _("En pausa")
        INACTIVE = "inactive", _("Inactivo")
        DISBANDED = "disbanded", _("Disuelto")

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="teams",
        verbose_name=_("organización"),
    )
    game = models.ForeignKey(
        Game,
        on_delete=models.PROTECT,
        related_name="teams",
        verbose_name=_("juego"),
    )
    name = models.CharField(_("nombre"), max_length=150)
    slug = models.SlugField(_("slug"), max_length=150)
    description = models.TextField(_("descripción"), blank=True)
    status = models.CharField(
        _("estado"), max_length=16, choices=Status.choices, default=Status.ACTIVE
    )
    founded_date = models.DateField(_("fecha de fundación"), null=True, blank=True)
    created_at = models.DateTimeField(_("creado"), auto_now_add=True)
    updated_at = models.DateTimeField(_("actualizado"), auto_now=True)

    class Meta:
        verbose_name = _("equipo")
        verbose_name_plural = _("equipos")
        ordering = ["organization", "game", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "slug"], name="unique_team_slug_per_org"
            ),
            models.UniqueConstraint(
                fields=["organization", "game", "name"],
                name="unique_team_name_per_org_game",
            ),
        ]
        indexes = [
            models.Index(fields=["game", "status"]),
        ]

    def __str__(self):
        return self.name

    @property
    def head_coach(self):
        """Nombre del entrenador principal activo del equipo, si lo hay."""
        assignment = (
            self.staff_assignments.filter(
                role="head_coach", ended_at__isnull=True
            )
            .select_related("staff")
            .first()
        )
        return assignment.staff.full_name if assignment else None

    @property
    def players_count(self):
        """Jugadores con asignación abierta en el equipo."""
        return self.player_assignments.filter(left_at__isnull=True).count()

    @property
    def winrate(self):
        """Porcentaje de victorias en partidos finalizados (0-100)."""
        finished = self.home_matches.filter(status="finished").values_list(
            "home_score", "away_score"
        )
        played = 0
        wins = 0
        for home_score, away_score in finished:
            if home_score is None or away_score is None:
                continue
            played += 1
            if home_score > away_score:
                wins += 1
        return round(wins / played * 100, 1) if played else 0
