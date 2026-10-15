from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class Tournament(models.Model):
    """Competición organizada (imagen, formato y número de participantes).

    Es una entidad global: cualquier usuario autenticado puede consultarla,
    pero solo el staff administra su creación y edición. Los partidos se
    asocian opcionalmente mediante :attr:`Match.tournament`.
    """

    class Format(models.TextChoices):
        SWISS = "swiss", _("Suizo")
        SINGLE_ELIMINATION = "single_elimination", _("Eliminación simple (Playoffs)")
        DOUBLE_ELIMINATION = "double_elimination", _("Eliminación doble")
        ROUND_ROBIN = "round_robin", _("Round Robin (liga)")
        GROUPS_PLAYOFFS = "groups_playoffs", _("Grupos + Playoffs")

    name = models.CharField(_("nombre"), max_length=150)
    slug = models.SlugField(_("slug"), max_length=160, unique=True, blank=True)
    game = models.ForeignKey(
        "organizations.Game",
        on_delete=models.PROTECT,
        related_name="tournaments",
        verbose_name=_("juego"),
    )
    format = models.CharField(
        _("formato"), max_length=32, choices=Format.choices, default=Format.SWISS
    )
    participants_count = models.PositiveSmallIntegerField(
        _("participantes"),
        default=2,
        validators=[MinValueValidator(2)],
        help_text=_("Número de participantes del torneo."),
    )
    groups_count = models.PositiveSmallIntegerField(
        _("número de grupos"),
        default=2,
        validators=[MinValueValidator(1)],
        help_text=_("Cantidad de grupos (solo para el formato Grupos + Playoffs)."),
    )
    image = models.ImageField(
        _("imagen"),
        upload_to="tournaments/images/",
        blank=True,
        null=True,
        help_text=_("Imagen representativa del torneo."),
    )
    image_url = models.URLField(_("imagen (URL)"), blank=True)
    start_date = models.DateField(_("fecha de inicio"), null=True, blank=True)
    end_date = models.DateField(_("fecha de fin"), null=True, blank=True)
    description = models.TextField(_("descripción"), blank=True)
    created_at = models.DateTimeField(_("creado"), auto_now_add=True)
    updated_at = models.DateTimeField(_("actualizado"), auto_now=True)

    class Meta:
        verbose_name = _("torneo")
        verbose_name_plural = _("torneos")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["game", "name"], name="unique_tournament_name_per_game"
            )
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:150] or "torneo"
            slug = base
            suffix = 2
            while (
                Tournament.objects.filter(slug=slug)
                .exclude(pk=self.pk)
                .exists()
            ):
                slug = f"{base}-{suffix}"
                suffix += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def image_display(self):
        """URL de la imagen: archivo subido si existe, si no el enlace externo."""
        if self.image:
            return self.image.url
        return self.image_url

    @property
    def participants_total(self):
        """Número de participantes realmente inscritos."""
        return self.participants.count()

    @property
    def has_participants_mismatch(self):
        """True si lo inscrito no coincide con lo especificado en el torneo."""
        return self.participants_total != self.participants_count


class TournamentParticipant(models.Model):
    """Inscripción de un equipo registrado en un torneo.

    El equipo debe pertenecer al juego del torneo. ``seed`` define su posición
    (siembra) y ``group_name`` su grupo en los formatos con fase de grupos.
    """

    tournament = models.ForeignKey(
        Tournament,
        on_delete=models.CASCADE,
        related_name="participants",
        verbose_name=_("torneo"),
    )
    team = models.ForeignKey(
        "organizations.Team",
        on_delete=models.PROTECT,
        related_name="tournament_participations",
        verbose_name=_("equipo"),
    )
    seed = models.PositiveSmallIntegerField(
        _("posición"), null=True, blank=True, help_text=_("Siembra u orden dentro del torneo.")
    )
    group_name = models.CharField(
        _("grupo"), max_length=8, blank=True, help_text=_("Grupo (p. ej. A, B, C).")
    )
    created_at = models.DateTimeField(_("creado"), auto_now_add=True)

    class Meta:
        verbose_name = _("participante")
        verbose_name_plural = _("participantes")
        ordering = ["seed", "team__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tournament", "team"],
                name="unique_participant_per_tournament",
            )
        ]

    def __str__(self):
        return f"{self.team} · {self.tournament}"

    def clean(self):
        """El equipo inscrito debe compartir el juego del torneo."""
        super().clean()
        if (
            self.team_id
            and self.tournament_id
            and self.team.game_id != self.tournament.game_id
        ):
            raise ValidationError(
                {"team": _("El equipo debe pertenecer al juego del torneo.")}
            )


class StatDefinition(models.Model):
    """Definición de una métrica estadística para un juego concreto.

    Evita asumir que todos los títulos comparten las mismas métricas: cada
    juego declara sus propias estadísticas (kills, ACS, CS/min, etc.) y su
    forma de agregación. Los valores medidos se guardan en tablas de hechos.
    """

    class Scope(models.TextChoices):
        PLAYER = "player", _("Jugador")
        TEAM = "team", _("Equipo")

    class Aggregation(models.TextChoices):
        SUM = "sum", _("Suma")
        AVG = "avg", _("Promedio")
        MAX = "max", _("Máximo")
        MIN = "min", _("Mínimo")
        LAST = "last", _("Último")

    game = models.ForeignKey(
        "organizations.Game",
        on_delete=models.CASCADE,
        related_name="stat_definitions",
        verbose_name=_("juego"),
    )
    scope = models.CharField(_("alcance"), max_length=8, choices=Scope.choices)
    code = models.SlugField(_("código"), max_length=60)
    name = models.CharField(_("nombre"), max_length=100)
    unit = models.CharField(_("unidad"), max_length=20, blank=True)
    aggregation = models.CharField(
        _("agregación"), max_length=8, choices=Aggregation.choices, default=Aggregation.SUM
    )
    higher_is_better = models.BooleanField(_("mayor es mejor"), default=True)
    is_active = models.BooleanField(_("activa"), default=True)
    created_at = models.DateTimeField(_("creado"), auto_now_add=True)
    updated_at = models.DateTimeField(_("actualizado"), auto_now=True)

    class Meta:
        verbose_name = _("definición de estadística")
        verbose_name_plural = _("definiciones de estadísticas")
        ordering = ["game", "scope", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["game", "scope", "code"], name="unique_stat_code_per_game_scope"
            )
        ]

    def __str__(self):
        return f"{self.name} [{self.game.short_name or self.game.name}]"


class Match(models.Model):
    """Partido, torneo o scrim disputado (o a disputar) por un equipo.

    Ambos participantes (``home_team`` y ``away_team``) deben ser equipos
    registrados en la plataforma. El resultado se gestiona aparte, ya que un
    partido puede comenzar sin marcador y actualizarse en vivo.
    """

    class Kind(models.TextChoices):
        OFFICIAL = "official", _("Oficial")
        TOURNAMENT = "tournament", _("Torneo")
        SCRIM = "scrim", _("Scrim")
        FRIENDLY = "friendly", _("Amistoso")

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", _("Programado")
        LIVE = "live", _("En vivo")
        FINISHED = "finished", _("Finalizado")
        CANCELLED = "cancelled", _("Cancelado")
        POSTPONED = "postponed", _("Aplazado")

    game = models.ForeignKey(
        "organizations.Game",
        on_delete=models.PROTECT,
        related_name="matches",
        verbose_name=_("juego"),
    )
    home_team = models.ForeignKey(
        "organizations.Team",
        on_delete=models.PROTECT,
        related_name="home_matches",
        verbose_name=_("equipo local"),
    )
    away_team = models.ForeignKey(
        "organizations.Team",
        on_delete=models.PROTECT,
        related_name="away_matches",
        verbose_name=_("equipo visitante"),
    )
    kind = models.CharField(
        _("tipo"), max_length=16, choices=Kind.choices, default=Kind.OFFICIAL
    )
    status = models.CharField(
        _("estado"), max_length=16, choices=Status.choices, default=Status.SCHEDULED
    )
    scheduled_at = models.DateTimeField(_("fecha y hora"))
    tournament = models.ForeignKey(
        Tournament,
        on_delete=models.SET_NULL,
        related_name="matches",
        null=True,
        blank=True,
        verbose_name=_("torneo"),
    )
    best_of = models.PositiveSmallIntegerField(_("al mejor de"), default=1)
    home_score = models.PositiveSmallIntegerField(_("marcador local"), null=True, blank=True)
    away_score = models.PositiveSmallIntegerField(_("marcador visitante"), null=True, blank=True)
    notes = models.TextField(_("notas tácticas"), blank=True)
    created_at = models.DateTimeField(_("creado"), auto_now_add=True)
    updated_at = models.DateTimeField(_("actualizado"), auto_now=True)

    class Meta:
        verbose_name = _("partido")
        verbose_name_plural = _("partidos")
        ordering = ["-scheduled_at"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(home_team=F("away_team")),
                name="match_teams_must_differ",
            ),
            models.CheckConstraint(
                condition=(
                    ~Q(status="finished")
                    | (Q(home_score__isnull=False) & Q(away_score__isnull=False))
                ),
                name="finished_match_requires_scores",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "scheduled_at"]),
            models.Index(fields=["game", "scheduled_at"]),
        ]

    def clean(self):
        """Reglas que cruzan tablas y no caben en un CHECK de columna."""
        super().clean()
        errors = {}
        if self.home_team_id and self.game_id and self.home_team.game_id != self.game_id:
            errors["home_team"] = _(
                "El equipo local debe pertenecer al juego del partido."
            )
        if self.away_team_id and self.game_id and self.away_team.game_id != self.game_id:
            errors["away_team"] = _(
                "El equipo visitante debe pertenecer al juego del partido."
            )
        if self.tournament_id:
            if self.game_id and self.tournament.game_id != self.game_id:
                errors["tournament"] = _(
                    "El torneo debe pertenecer al juego del partido."
                )
            else:
                enrolled_team_ids = set(
                    self.tournament.participants.values_list("team_id", flat=True)
                )
                if self.home_team_id and self.home_team_id not in enrolled_team_ids:
                    errors["home_team"] = _(
                        "El equipo local no está inscrito en el torneo seleccionado."
                    )
                if self.away_team_id and self.away_team_id not in enrolled_team_ids:
                    errors["away_team"] = _(
                        "El equipo visitante no está inscrito en el torneo seleccionado."
                    )
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.home_team} vs {self.away_team} ({self.scheduled_at:%Y-%m-%d})"

    @property
    def opponent(self):
        """Nombre del equipo rival (siempre un equipo registrado)."""
        return self.away_team.name if self.away_team_id else "—"

    @property
    def is_finished(self):
        return self.status == self.Status.FINISHED

    @property
    def is_live(self):
        return self.status == self.Status.LIVE

    @property
    def has_score(self):
        """True si el partido ya tiene marcador (en vivo o finalizado)."""
        return self.home_score is not None and self.away_score is not None

    @property
    def winner(self):
        """Equipo ganador del partido finalizado, si puede determinarse."""
        if not self.is_finished:
            return None
        if self.home_score is None or self.away_score is None:
            return None
        if self.home_score > self.away_score:
            return self.home_team
        if self.away_score > self.home_score:
            return self.away_team
        return None


class MatchMap(models.Model):
    """Mapa individual dentro de una serie (cuando corresponde).

    Permite registrar series al mejor de N sin asumir que todos los partidos
    son de un único mapa.
    """

    class Outcome(models.TextChoices):
        HOME = "home", _("Local")
        AWAY = "away", _("Visitante")
        DRAW = "draw", _("Empate")

    match = models.ForeignKey(
        Match,
        on_delete=models.CASCADE,
        related_name="maps",
        verbose_name=_("partido"),
    )
    order = models.PositiveSmallIntegerField(_("orden"))
    map_name = models.CharField(_("mapa"), max_length=100)
    home_score = models.PositiveSmallIntegerField(_("marcador local"), default=0)
    away_score = models.PositiveSmallIntegerField(_("marcador visitante"), default=0)
    outcome = models.CharField(
        _("resultado"), max_length=8, choices=Outcome.choices, blank=True
    )
    created_at = models.DateTimeField(_("creado"), auto_now_add=True)
    updated_at = models.DateTimeField(_("actualizado"), auto_now=True)

    class Meta:
        verbose_name = _("mapa de partido")
        verbose_name_plural = _("mapas de partido")
        ordering = ["match", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["match", "order"], name="unique_map_order_per_match"
            )
        ]

    def __str__(self):
        return f"{self.match} · mapa {self.order}: {self.map_name}"


class PlayerMatchStat(models.Model):
    """Valor de una métrica de jugador registrado en un partido."""

    match = models.ForeignKey(
        Match,
        on_delete=models.CASCADE,
        related_name="player_stats",
        verbose_name=_("partido"),
    )
    player = models.ForeignKey(
        "players.Player",
        on_delete=models.PROTECT,
        related_name="match_stats",
        verbose_name=_("jugador"),
    )
    definition = models.ForeignKey(
        StatDefinition,
        on_delete=models.PROTECT,
        related_name="player_values",
        verbose_name=_("definición"),
    )
    value = models.DecimalField(_("valor"), max_digits=12, decimal_places=3)
    created_at = models.DateTimeField(_("creado"), auto_now_add=True)
    updated_at = models.DateTimeField(_("actualizado"), auto_now=True)

    class Meta:
        verbose_name = _("estadística de jugador")
        verbose_name_plural = _("estadísticas de jugadores")
        ordering = ["match", "player", "definition"]
        constraints = [
            models.UniqueConstraint(
                fields=["match", "player", "definition"],
                name="unique_player_stat_per_match",
            )
        ]
        indexes = [
            models.Index(fields=["player", "definition"]),
        ]

    def clean(self):
        """Valida coherencia entre métrica, juego y participantes."""
        super().clean()
        if self.definition_id and self.definition.scope != StatDefinition.Scope.PLAYER:
            raise ValidationError(
                {"definition": _("La métrica seleccionada no es de alcance 'jugador'.")}
            )
        if (
            self.definition_id
            and self.match_id
            and self.definition.game_id != self.match.game_id
        ):
            raise ValidationError(
                {"definition": _("La métrica debe pertenecer al juego del partido.")}
            )

    def __str__(self):
        return f"{self.player} · {self.definition.code}={self.value}"


class TeamMatchStat(models.Model):
    """Valor de una métrica de equipo registrado en un partido (o serie)."""

    match = models.ForeignKey(
        Match,
        on_delete=models.CASCADE,
        related_name="team_stats",
        verbose_name=_("partido"),
    )
    team = models.ForeignKey(
        "organizations.Team",
        on_delete=models.PROTECT,
        related_name="match_stats",
        verbose_name=_("equipo"),
    )
    definition = models.ForeignKey(
        StatDefinition,
        on_delete=models.PROTECT,
        related_name="team_values",
        verbose_name=_("definición"),
    )
    value = models.DecimalField(
        _("valor"), max_digits=12, decimal_places=3, default=Decimal("0")
    )
    created_at = models.DateTimeField(_("creado"), auto_now_add=True)
    updated_at = models.DateTimeField(_("actualizado"), auto_now=True)

    class Meta:
        verbose_name = _("estadística de equipo")
        verbose_name_plural = _("estadísticas de equipos")
        ordering = ["match", "team", "definition"]
        constraints = [
            models.UniqueConstraint(
                fields=["match", "team", "definition"],
                name="unique_team_stat_per_match",
            )
        ]

    def clean(self):
        super().clean()
        if self.definition_id and self.definition.scope != StatDefinition.Scope.TEAM:
            raise ValidationError(
                {"definition": _("La métrica seleccionada no es de alcance 'equipo'.")}
            )
        if (
            self.definition_id
            and self.match_id
            and self.definition.game_id != self.match.game_id
        ):
            raise ValidationError(
                {"definition": _("La métrica debe pertenecer al juego del partido.")}
            )

    def __str__(self):
        return f"{self.team} · {self.definition.code}={self.value}"
