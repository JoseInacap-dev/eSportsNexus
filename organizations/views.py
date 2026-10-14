from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Prefetch, Q
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from accounts.models import OrganizationMembership
from core.mixins import OrganizationAccessMixin
from core.permissions import user_can_manage_organization, user_manages_any_organization
from organizations.forms import OrganizationForm, TeamForm
from organizations.models import COACH_ROLE_NAME, Game, Organization, Team
from players.models import PlayerTeamAssignment


class TeamListView(LoginRequiredMixin, ListView):
    model = Team
    template_name = "equipos/lista.html"
    context_object_name = "equipos"
    paginate_by = 20

    def get_queryset(self):
        queryset = Team.objects.select_related("organization", "game")
        user = self.request.user
        if not user.is_superuser:
            queryset = queryset.filter(
                organization__memberships__user=user,
                organization__memberships__is_active=True,
            ).distinct()

        search = self.request.GET.get("q")
        if search:
            queryset = queryset.filter(name__icontains=search)
        game_id = self.request.GET.get("juego")
        if game_id:
            queryset = queryset.filter(game_id=game_id)
        status = self.request.GET.get("estado")
        if status:
            queryset = queryset.filter(status=status)
        return queryset.prefetch_related(
            Prefetch(
                "player_assignments",
                queryset=PlayerTeamAssignment.objects.filter(
                    left_at__isnull=True,
                    competitive_role__name=COACH_ROLE_NAME,
                ).select_related("player", "competitive_role"),
                to_attr="_coach_assignments",
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_manage"] = user_manages_any_organization(self.request.user)
        context["juegos_disponibles"] = Game.objects.filter(is_active=True)
        return context


class TeamDetailView(OrganizationAccessMixin, DetailView):
    model = Team
    template_name = "equipos/detalle.html"
    context_object_name = "equipo"

    def get_organization(self):
        return self.get_object().organization

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        team = self.object
        assignments = list(
            team.player_assignments.filter(left_at__isnull=True)
            .select_related("player", "competitive_role")
            .order_by("player__nickname")
        )
        context["jugadores"] = [
            a
            for a in assignments
            if not (a.competitive_role and a.competitive_role.name == COACH_ROLE_NAME)
        ]
        context["coaches"] = [
            a
            for a in assignments
            if a.competitive_role and a.competitive_role.name == COACH_ROLE_NAME
        ]
        context["staff_assignments"] = team.staff_assignments.select_related(
            "staff"
        ).order_by("-started_at")
        context["partidos"] = team.home_matches.select_related(
            "game", "away_team"
        ).order_by("-scheduled_at")[:10]
        context["estadisticas"] = self._stats(team)
        context["can_manage"] = user_can_manage_organization(
            self.request.user, team.organization
        )
        return context

    @staticmethod
    def _stats(team):
        scores = list(
            team.home_matches.filter(status="finished").values_list(
                "home_score", "away_score"
            )
        )
        played = [s for s in scores if s[0] is not None and s[1] is not None]
        victorias = sum(1 for h, a in played if h > a)
        derrotas = len(played) - victorias
        return {
            "victorias": victorias,
            "derrotas": derrotas,
            "winrate": round(victorias / len(played) * 100, 1) if played else 0,
        }



class TeamCreateView(LoginRequiredMixin, CreateView):
    model = Team
    form_class = TeamForm
    template_name = "equipos/form.html"
    success_url = reverse_lazy("organizations:team-list")
    extra_context = {"form_title": "Nuevo equipo"}

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        organization = form.cleaned_data["organization"]
        if not user_can_manage_organization(self.request.user, organization):
            raise PermissionDenied("No puedes crear equipos en esa organización.")
        messages.success(self.request, "Equipo creado correctamente.")
        return super().form_valid(form)


class TeamUpdateView(OrganizationAccessMixin, UpdateView):
    model = Team
    form_class = TeamForm
    template_name = "equipos/form.html"
    success_url = reverse_lazy("organizations:team-list")
    require_manage = True
    extra_context = {"form_title": "Editar equipo"}

    def get_organization(self):
        return self.get_object().organization

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        organization = form.cleaned_data["organization"]
        if not user_can_manage_organization(self.request.user, organization):
            raise PermissionDenied("No puedes mover el equipo a esa organización.")
        messages.success(self.request, "Equipo actualizado correctamente.")
        return super().form_valid(form)


class TeamDeleteView(OrganizationAccessMixin, DeleteView):
    model = Team
    template_name = "confirmar_eliminar.html"
    success_url = reverse_lazy("organizations:team-list")
    require_manage = True

    def get_organization(self):
        return self.get_object().organization

    def form_valid(self, form):
        messages.success(self.request, "Equipo eliminado.")
        return super().form_valid(form)


class OrganizationListView(LoginRequiredMixin, ListView):
    model = Organization
    template_name = "organizaciones/lista.html"
    context_object_name = "organizaciones"
    paginate_by = 20

    def get_queryset(self):
        queryset = Organization.objects.annotate(
            teams_count=Count("teams", distinct=True)
        ).order_by("name")
        user = self.request.user
        if not user.is_superuser:
            queryset = queryset.filter(
                memberships__user=user,
                memberships__is_active=True,
            ).distinct()

        search = self.request.GET.get("q")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(abbreviation__icontains=search)
                | Q(country__icontains=search)
            )
        status = self.request.GET.get("estado")
        if status == "activas":
            queryset = queryset.filter(is_active=True)
        elif status == "inactivas":
            queryset = queryset.filter(is_active=False)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_manage"] = user_manages_any_organization(self.request.user)
        return context


class OrganizationDetailView(OrganizationAccessMixin, DetailView):
    model = Organization
    template_name = "organizaciones/detalle.html"
    context_object_name = "organizacion"

    def get_organization(self):
        return self.get_object()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = self.object
        context["equipos"] = organization.teams.select_related("game").order_by(
            "game__name", "name"
        )
        context["memberships"] = organization.memberships.select_related(
            "user"
        ).order_by("role", "user__username")
        context["can_manage"] = user_can_manage_organization(
            self.request.user, organization
        )
        return context


class OrganizationCreateView(LoginRequiredMixin, CreateView):
    model = Organization
    form_class = OrganizationForm
    template_name = "organizaciones/form.html"
    extra_context = {"form_title": "Nueva organización"}

    def form_valid(self, form):
        with transaction.atomic():
            response = super().form_valid(form)
            OrganizationMembership.objects.get_or_create(
                user=self.request.user,
                organization=self.object,
                defaults={
                    "role": OrganizationMembership.Role.OWNER,
                    "is_active": True,
                },
            )
        messages.success(self.request, "Organización creada correctamente.")
        return response

    def get_success_url(self):
        return reverse("organizations:organization-detail", args=[self.object.pk])


class OrganizationUpdateView(OrganizationAccessMixin, UpdateView):
    model = Organization
    form_class = OrganizationForm
    template_name = "organizaciones/form.html"
    require_manage = True
    extra_context = {"form_title": "Editar organización"}

    def get_organization(self):
        return self.get_object()

    def form_valid(self, form):
        messages.success(self.request, "Organización actualizada correctamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("organizations:organization-detail", args=[self.object.pk])
