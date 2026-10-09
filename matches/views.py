from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from core.mixins import OrganizationAccessMixin
from core.permissions import user_can_manage_organization
from matches.forms import MatchForm
from matches.models import Match
from organizations.models import Team


class MatchListView(LoginRequiredMixin, ListView):
    model = Match
    template_name = "partidos/lista.html"
    context_object_name = "partidos"
    paginate_by = 20

    def get_queryset(self):
        queryset = Match.objects.select_related(
            "game", "home_team", "home_team__organization", "away_team"
        )
        user = self.request.user
        if not user.is_superuser:
            queryset = queryset.filter(
                home_team__organization__memberships__user=user,
                home_team__organization__memberships__is_active=True,
            ).distinct()

        team_id = self.request.GET.get("equipo")
        if team_id:
            queryset = queryset.filter(home_team_id=team_id)
        kind = self.request.GET.get("tipo")
        if kind:
            queryset = queryset.filter(kind=kind)
        status = self.request.GET.get("estado")
        if status:
            queryset = queryset.filter(status=status)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["statuses"] = Match.Status.choices
        context["kinds"] = Match.Kind.choices
        context["equipos_disponibles"] = Team.objects.select_related(
            "organization", "game"
        ).order_by("name")
        return context


class MatchDetailView(OrganizationAccessMixin, DetailView):
    model = Match
    template_name = "partidos/detalle.html"
    context_object_name = "match"

    def get_organization(self):
        return self.get_object().home_team.organization

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        match = self.object
        context["maps"] = match.maps.all()
        context["player_stats"] = match.player_stats.select_related(
            "player", "definition"
        ).order_by("player__nickname", "definition__name")
        context["team_stats"] = match.team_stats.select_related(
            "team", "definition"
        )
        return context


class MatchCreateView(LoginRequiredMixin, CreateView):
    model = Match
    form_class = MatchForm
    template_name = "partidos/form.html"
    success_url = reverse_lazy("matches:match-list")
    extra_context = {"form_title": "Nuevo partido"}

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        home_team = form.cleaned_data["home_team"]
        if not user_can_manage_organization(self.request.user, home_team.organization):
            raise PermissionDenied("No puedes registrar partidos para ese equipo.")
        messages.success(self.request, "Partido creado correctamente.")
        return super().form_valid(form)


class MatchUpdateView(OrganizationAccessMixin, UpdateView):
    model = Match
    form_class = MatchForm
    template_name = "partidos/form.html"
    success_url = reverse_lazy("matches:match-list")
    require_manage = True
    extra_context = {"form_title": "Editar partido"}

    def get_organization(self):
        return self.get_object().home_team.organization

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        home_team = form.cleaned_data["home_team"]
        if not user_can_manage_organization(self.request.user, home_team.organization):
            raise PermissionDenied("No puedes modificar ese partido.")
        messages.success(self.request, "Partido actualizado correctamente.")
        return super().form_valid(form)