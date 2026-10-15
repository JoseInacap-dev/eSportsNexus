from django import forms
from django.forms import inlineformset_factory

from core.permissions import MANAGEMENT_ROLES
from core.widgets import NexusDateInput, NexusDateTimeInput, TeamCheckboxGrid
from matches.models import Match, Tournament, TournamentParticipant
from organizations.models import Organization, Team


class MatchForm(forms.ModelForm):
    class Meta:
        model = Match
        fields = [
            "game",
            "home_team",
            "away_team",
            "kind",
            "status",
            "scheduled_at",
            "tournament",
            "best_of",
            "notes",
        ]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        def visible_organizations():
            if user is not None and user.is_superuser:
                return Organization.objects.all()
            return Organization.objects.filter(
                memberships__user=user, memberships__is_active=True
            ).distinct()

        def manageable_organizations():
            if user is not None and user.is_superuser:
                return Organization.objects.all()
            return Organization.objects.filter(
                memberships__user=user,
                memberships__is_active=True,
                memberships__role__in=MANAGEMENT_ROLES,
            ).distinct()

        visible_orgs = visible_organizations()
        self.fields["home_team"].queryset = Team.objects.filter(
            organization__in=manageable_organizations()
        ).select_related("organization", "game")
        self.fields["away_team"].queryset = Team.objects.filter(
            organization__in=visible_orgs
        ).select_related("organization", "game")
        self.fields["tournament"].queryset = Tournament.objects.select_related(
            "game"
        ).order_by("name")
        self.fields["tournament"].required = False

        self.fields["scheduled_at"].widget = NexusDateTimeInput()
        self.fields["scheduled_at"].input_formats = [
            "%Y-%m-%d %H:%M",
            "%Y-%m-%dT%H:%M",
        ]


class TournamentForm(forms.ModelForm):
    """Formulario de torneo con selección múltiple de equipos participantes.

    La cantidad de participantes es solo una referencia: si al guardar el
    número de equipos seleccionados no coincide con ``participants_count`` se
    avisará al usuario, pero no se bloquea el guardado. Los equipos sí deben
    pertenecer al juego del torneo (esto último es un error de validación).
    """

    participants = forms.ModelMultipleChoiceField(
        queryset=Team.objects.none(),
        required=False,
        widget=TeamCheckboxGrid,
        label="Equipos participantes",
        help_text="Selecciona los equipos inscritos. Deben pertenecer al juego del torneo.",
    )

    class Meta:
        model = Tournament
        fields = [
            "name",
            "game",
            "format",
            "participants_count",
            "groups_count",
            "image",
            "image_url",
            "start_date",
            "end_date",
            "description",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "start_date": NexusDateInput(),
            "end_date": NexusDateInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["start_date"].input_formats = ["%Y-%m-%d"]
        self.fields["end_date"].input_formats = ["%Y-%m-%d"]

        teams = Team.objects.select_related("organization", "game").order_by("name")
        self.fields["participants"].queryset = teams
        self.fields["participants"].widget.games = {
            str(team.pk): str(team.game_id) for team in teams
        }
        if self.instance.pk:
            self.fields["participants"].initial = self.instance.participants.values_list(
                "team_id", flat=True
            )

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_date")
        end = cleaned.get("end_date")
        if start and end and end < start:
            self.add_error(
                "end_date", "La fecha de fin no puede ser anterior a la de inicio."
            )

        game = cleaned.get("game")
        participants = cleaned.get("participants")
        if game and participants:
            wrong = [team.name for team in participants if team.game_id != game.pk]
            if wrong:
                self.add_error(
                    "participants",
                    "Estos equipos no pertenecen al juego del torneo: "
                    + ", ".join(wrong)
                    + ".",
                )
        return cleaned

    def save(self, commit=True):
        tournament = super().save(commit=commit)
        if commit:
            self._sync_participants(tournament)
        return tournament

    def _sync_participants(self, tournament):
        """Sincroniza las inscripciones preservando grupo y seed manuales."""
        selected = list(self.cleaned_data.get("participants") or [])
        selected_ids = {team.pk for team in selected}
        existing = {p.team_id: p for p in tournament.participants.all()}

        for team_id, participant in existing.items():
            if team_id not in selected_ids:
                participant.delete()

        next_seed = max(
            [p.seed or 0 for team_id, p in existing.items() if team_id in selected_ids]
            or [0]
        )
        groups = self._group_labels(tournament)
        for team in selected:
            if team.pk in existing:
                continue
            next_seed += 1
            group_name = ""
            if groups:
                group_name = groups[(next_seed - 1) % len(groups)]
            TournamentParticipant.objects.create(
                tournament=tournament,
                team=team,
                seed=next_seed,
                group_name=group_name,
            )

    @staticmethod
    def _group_labels(tournament):
        """Letras de grupo disponibles para el reparto automático (o vacío)."""
        if tournament.format != Tournament.Format.GROUPS_PLAYOFFS:
            return []
        count = max(tournament.groups_count or 1, 1)
        return [chr(ord("A") + index) for index in range(count)]


class TournamentParticipantForm(forms.ModelForm):
    """Fila editable de un participante (equipo, grupo y posición)."""

    class Meta:
        model = TournamentParticipant
        fields = ["team", "group_name", "seed"]

    def __init__(self, *args, tournament=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tournament = tournament or getattr(self.instance, "tournament", None)
        if self.tournament is not None:
            self.fields["team"].queryset = Team.objects.filter(
                game=self.tournament.game
            ).select_related("organization")
        else:
            self.fields["team"].queryset = Team.objects.none()
        self.fields["team"].label = "Equipo"
        self.fields["group_name"].label = "Grupo"
        self.fields["seed"].label = "Posición"

    def clean_team(self):
        team = self.cleaned_data.get("team")
        if team and self.tournament and team.game_id != self.tournament.game_id:
            raise forms.ValidationError("El equipo debe pertenecer al juego del torneo.")
        return team


TournamentParticipantFormSet = inlineformset_factory(
    Tournament,
    TournamentParticipant,
    form=TournamentParticipantForm,
    fields=["team", "group_name", "seed"],
    extra=1,
    can_delete=True,
)
