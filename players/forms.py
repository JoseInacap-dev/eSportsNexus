from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.permissions import MANAGEMENT_ROLES
from core.widgets import NexusDateInput
from organizations.models import GameRole, Team
from players.models import Player, PlayerTeamAssignment


class PlayerForm(forms.ModelForm):
    class Meta:
        model = Player
        fields = [
            "player_type",
            "first_name",
            "last_name",
            "nickname",
            "email",
            "phone",
            "birth_date",
            "country",
        ]
        widgets = {"birth_date": NexusDateInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["birth_date"].input_formats = ["%Y-%m-%d"]


class PlayerTeamAssignmentForm(forms.ModelForm):
    """Alta de un jugador en un equipo.

    Funciona en dos modos:

    * Modo equipo (``team`` fijo): se elige o se crea un jugador para ese
      equipo. Es el flujo usado desde la ficha del equipo.
    * Modo jugador (``player`` fijo): se elige el equipo destino. Es el flujo
      usado desde la ficha del jugador.
    """

    new_player_first_name = forms.CharField(
        label=_("Nombre (nuevo jugador)"), max_length=80, required=False
    )
    new_player_last_name = forms.CharField(
        label=_("Apellidos (nuevo jugador)"), max_length=80, required=False
    )
    new_player_nickname = forms.CharField(
        label=_("Nickname (nuevo jugador)"), max_length=60, required=False
    )
    new_player_country = forms.CharField(
        label=_("País (nuevo jugador)"), max_length=60, required=False
    )

    class Meta:
        model = PlayerTeamAssignment
        fields = [
            "team",
            "player",
            "competitive_role",
            "joined_at",
            "status",
            "is_captain",
            "notes",
        ]
        widgets = {
            "joined_at": NexusDateInput(),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, user=None, team=None, player=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fixed_team = team
        self.fixed_player = player

        self.fields["player"].required = False
        self.fields["competitive_role"].required = False
        self.fields["joined_at"].initial = (
            self.fields["joined_at"].initial or timezone.localdate()
        )
        self.fields["joined_at"].input_formats = ["%Y-%m-%d"]

        base_players = Player.objects.filter(player_type=Player.PlayerType.PLAYER)

        if team is not None:
            # Modo equipo: el equipo queda fijo y no se muestra su selector.
            self.instance.team = team
            self.fields.pop("team", None)
            busy_players = PlayerTeamAssignment.objects.filter(
                left_at__isnull=True
            ).values_list("player_id", flat=True)
            self.fields["player"].queryset = base_players.exclude(
                pk__in=busy_players
            ).order_by("nickname")
            self.fields["competitive_role"].queryset = GameRole.objects.filter(
                game=team.game
            ).order_by("name")
        elif player is not None:
            # Modo jugador: el jugador queda fijo y no se muestra su selector,
            # ni tiene sentido ofrecer crear uno nuevo.
            self.instance.player = player
            for name in (
                "player",
                "new_player_first_name",
                "new_player_last_name",
                "new_player_nickname",
                "new_player_country",
            ):
                self.fields.pop(name, None)
            teams = Team.objects.select_related("organization", "game")
            if user is not None and not user.is_superuser:
                teams = teams.filter(
                    organization__memberships__user=user,
                    organization__memberships__is_active=True,
                    organization__memberships__role__in=MANAGEMENT_ROLES,
                ).distinct()
            self.fields["team"].queryset = teams.order_by("name")
            self.fields["competitive_role"].queryset = GameRole.objects.order_by(
                "game__name", "name"
            )

    def clean(self):
        cleaned = super().clean()
        # El jugador puede venir fijo (modo jugador) o elegirse aquí (modo equipo).
        if self.fixed_player is not None:
            return cleaned

        player = cleaned.get("player")
        new_nickname = (cleaned.get("new_player_nickname") or "").strip()
        new_first_name = (cleaned.get("new_player_first_name") or "").strip()
        creating_new = any(
            (cleaned.get(name) or "").strip()
            for name in (
                "new_player_first_name",
                "new_player_last_name",
                "new_player_nickname",
                "new_player_country",
            )
        )

        if creating_new and player:
            self.add_error(
                "player",
                _("Elegí un jugador existente o creá uno nuevo, no ambos."),
            )
        elif not creating_new and not player:
            self.add_error(
                "player",
                _("Seleccioná un jugador existente o completá los datos del nuevo."),
            )
        elif creating_new:
            if not new_first_name:
                self.add_error(
                    "new_player_first_name",
                    _("El nombre es obligatorio para crear un jugador."),
                )
            if not new_nickname:
                self.add_error(
                    "new_player_nickname",
                    _("El nickname es obligatorio para crear un jugador."),
                )
            elif Player.objects.filter(nickname=new_nickname).exists():
                self.add_error(
                    "new_player_nickname",
                    _("Ya existe un jugador con ese nickname."),
                )
        return cleaned

    def save(self, commit=True):
        assignment = super().save(commit=False)
        if self.fixed_team is not None:
            assignment.team = self.fixed_team
        if self.fixed_player is not None:
            assignment.player = self.fixed_player
        elif assignment.player_id is None:
            assignment.player = Player.objects.create(
                player_type=Player.PlayerType.PLAYER,
                first_name=(self.cleaned_data["new_player_first_name"] or "").strip(),
                last_name=(self.cleaned_data["new_player_last_name"] or "").strip(),
                nickname=(self.cleaned_data["new_player_nickname"] or "").strip(),
                country=(self.cleaned_data["new_player_country"] or "").strip(),
            )
        if commit:
            assignment.save()
        return assignment


class AssignmentFinishForm(forms.ModelForm):
    """Cierre de una asignación: registra la fecha de baja."""

    class Meta:
        model = PlayerTeamAssignment
        fields = ["left_at"]
        widgets = {
            "left_at": NexusDateInput()
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["left_at"].required = True
        self.fields["left_at"].initial = (
            self.fields["left_at"].initial or timezone.localdate()
        )
        self.fields["left_at"].input_formats = ["%Y-%m-%d"]
