from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DetailView,
    ListView,
    UpdateView,
)

from core.mixins import OrganizationAccessMixin
from core.permissions import (
    user_can_manage_organization,
    user_manages_any_organization,
)
from organizations.models import Team
from players.forms import (
    AssignmentFinishForm,
    PlayerForm,
    PlayerTeamAssignmentForm,
)
from players.models import Player, PlayerTeamAssignment


class PlayerListView(LoginRequiredMixin, ListView):
    model = Player
    template_name = "jugadores/lista.html"
    context_object_name = "jugadores"
    paginate_by = 20

    def get_queryset(self):
        queryset = Player.objects.prefetch_related("team_assignments__team").order_by(
            "nickname"
        )
        search = self.request.GET.get("q")
        if search:
            queryset = queryset.filter(nickname__icontains=search)
        team_id = self.request.GET.get("equipo")
        if team_id:
            queryset = queryset.filter(
                team_assignments__team_id=team_id,
                team_assignments__left_at__isnull=True,
            ).distinct()
        state = self.request.GET.get("estado")
        if state:
            queryset = queryset.filter(
                team_assignments__status=state,
                team_assignments__left_at__isnull=True,
            ).distinct()
        player_type = self.request.GET.get("tipo")
        if player_type:
            queryset = queryset.filter(player_type=player_type)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_manage"] = user_manages_any_organization(self.request.user)
        context["equipos_disponibles"] = Team.objects.select_related(
            "organization", "game"
        ).order_by("name")
        context["tipos_disponibles"] = Player.PlayerType.choices
        return context


class PlayerDetailView(LoginRequiredMixin, DetailView):
    model = Player
    template_name = "jugadores/detalle.html"
    context_object_name = "jugador"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        player = self.object
        context["active_assignment"] = player.current_assignment
        context["assignments"] = player.team_assignments.select_related(
            "team", "team__organization", "competitive_role"
        ).order_by("-joined_at")
        context["match_stats"] = player.match_stats.select_related(
            "match", "match__home_team", "match__away_team", "definition"
        ).order_by("-match__scheduled_at")[:20]
        context["can_manage"] = user_manages_any_organization(self.request.user)
        return context


class PlayerCreateView(LoginRequiredMixin, CreateView):
    model = Player
    form_class = PlayerForm
    template_name = "jugadores/form.html"
    success_url = reverse_lazy("players:player-list")
    extra_context = {"form_title": "Nuevo jugador"}

    def form_valid(self, form):
        if not user_manages_any_organization(self.request.user):
            raise PermissionDenied("Necesitas gestionar una organización.")
        messages.success(self.request, "Jugador creado correctamente.")
        return super().form_valid(form)


class PlayerUpdateView(LoginRequiredMixin, UpdateView):
    model = Player
    form_class = PlayerForm
    template_name = "jugadores/form.html"
    success_url = reverse_lazy("players:player-list")
    extra_context = {"form_title": "Editar jugador"}

    def form_valid(self, form):
        if not user_manages_any_organization(self.request.user):
            raise PermissionDenied("Necesitas gestionar una organización.")
        messages.success(self.request, "Jugador actualizado correctamente.")
        return super().form_valid(form)


class AssignmentCreateForTeamView(OrganizationAccessMixin, CreateView):
    """Agrega un jugador (existente o nuevo) a un equipo concreto."""

    model = PlayerTeamAssignment
    form_class = PlayerTeamAssignmentForm
    template_name = "jugadores/asignacion_form.html"
    require_manage = True

    def get_team(self):
        if not hasattr(self, "_team"):
            self._team = get_object_or_404(
                Team.objects.select_related("organization", "game"),
                pk=self.kwargs["team_pk"],
            )
        return self._team

    def get_organization(self):
        return self.get_team().organization

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        kwargs["team"] = self.get_team()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        team = self.get_team()
        context["equipo"] = team
        context["cancel_url"] = reverse(
            "organizations:team-detail", args=[team.pk]
        )
        context["form_title"] = f"Agregar jugador a {team.name}"
        return context

    def form_valid(self, form):
        messages.success(self.request, "Jugador agregado al equipo.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "organizations:team-detail", args=[self.get_team().pk]
        )


class AssignmentCreateForPlayerView(LoginRequiredMixin, CreateView):
    """Asigna un jugador concreto a uno de sus equipos."""

    model = PlayerTeamAssignment
    form_class = PlayerTeamAssignmentForm
    template_name = "jugadores/asignacion_form.html"

    def get_player(self):
        if not hasattr(self, "_player"):
            self._player = get_object_or_404(Player, pk=self.kwargs["player_pk"])
        return self._player

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        kwargs["player"] = self.get_player()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        player = self.get_player()
        context["jugador"] = player
        context["cancel_url"] = reverse(
            "players:player-detail", args=[player.pk]
        )
        context["form_title"] = f"Asignar a {player.nickname} a un equipo"
        return context

    def form_valid(self, form):
        team = form.cleaned_data["team"]
        if not user_can_manage_organization(self.request.user, team.organization):
            raise PermissionDenied("No puedes asignar jugadores a ese equipo.")
        messages.success(self.request, "Jugador asignado al equipo.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("players:player-detail", args=[self.get_player().pk])


class AssignmentFinishView(OrganizationAccessMixin, UpdateView):
    """Da de baja a un jugador del equipo (cierra la asignación)."""

    model = PlayerTeamAssignment
    form_class = AssignmentFinishForm
    template_name = "jugadores/asignacion_baja.html"
    context_object_name = "asignacion"
    require_manage = True

    def get_organization(self):
        return self.get_object().team.organization

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.status = PlayerTeamAssignment.Status.LEFT
        self.object.save()
        messages.success(self.request, "Jugador dado de baja del equipo.")
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse(
            "organizations:team-detail", args=[self.object.team_id]
        )
