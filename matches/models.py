from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils.translation import gettext_lazy as _


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

    ``home_team`` es siempre un equipo de la plataforma. El rival puede ser
    otro equipo registrado (``away_team``) o un oponente externo identificado
    por texto (``away_name``).
    """

    class Kind(models.TextChoices):
        OFFICIAL = "official", _("Oficial")
        TOURNAMENT = "tournament", _("Torneo")
        SCRIM = "scrim", _("Scrim")
        FRIENDLY = "friendly", _("Amistoso")

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", _("Programado")
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
        null=True,
        blank=True,
        related_name="away_matches",
        verbose_name=_("equipo visitante"),
    )
    away_name = models.CharField(
        _("rival externo"), max_length=150, blank=True
    )
    kind = models.CharField(
        _("tipo"), max_length=16, choices=Kind.choices, default=Kind.OFFICIAL
    )
    status = models.CharField(
        _("estado"), max_length=16, choices=Status.choices, default=Status.SCHEDULED
    )
    scheduled_at = models.DateTimeField(_("fecha y hora"))
    tournament_name = models.CharField(_("torneo"), max_length=150, blank=True)
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
                condition=Q(away_team__isnull=False) | ~Q(away_name=""),
                name="match_requires_opponent",
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
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        opponent = self.away_team or self.away_name or "?"
        return f"{self.home_team} vs {opponent} ({self.scheduled_at:%Y-%m-%d})"

    @property
    def opponent(self):
        """Nombre del rival, ya sea un equipo registrado o un nombre externo."""
        return self.away_team.name if self.away_team else (self.away_name or "—")

    @property
    def is_finished(self):
        return self.status == self.Status.FINISHED

    @property
    def is_live(self):
        return self.status == "live"

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
