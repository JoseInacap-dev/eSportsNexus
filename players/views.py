from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from core.permissions import user_manages_any_organization
from organizations.models import Team
from players.forms import PlayerForm
from players.models import Player


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
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_manage"] = user_manages_any_organization(self.request.user)
        context["equipos_disponibles"] = Team.objects.select_related(
            "organization", "game"
        ).order_by("name")
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
