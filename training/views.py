from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView

from core.permissions import user_can_manage_organization
from organizations.models import Team
from training.forms import TrainingSessionForm
from training.models import TrainingSession


class TrainingSessionListView(LoginRequiredMixin, ListView):
    model = TrainingSession
    template_name = "entrenamientos/lista.html"
    context_object_name = "entrenamientos"
    paginate_by = 20

    def get_queryset(self):
        queryset = TrainingSession.objects.select_related(
            "team", "team__organization", "team__game"
        )
        user = self.request.user
        if not user.is_superuser:
            queryset = queryset.filter(
                team__organization__memberships__user=user,
                team__organization__memberships__is_active=True,
            ).distinct()

        team_id = self.request.GET.get("equipo")
        if team_id:
            queryset = queryset.filter(team_id=team_id)
        status = self.request.GET.get("estado")
        if status:
            queryset = queryset.filter(status=status)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["equipos_disponibles"] = Team.objects.select_related(
            "organization", "game"
        ).order_by("name")
        context["statuses"] = TrainingSession.Status.choices
        return context


class TrainingSessionCreateView(LoginRequiredMixin, CreateView):
    model = TrainingSession
    form_class = TrainingSessionForm
    template_name = "entrenamientos/form.html"
    success_url = reverse_lazy("training:session-list")
    extra_context = {"form_title": "Nueva sesión de entrenamiento"}

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        team = form.cleaned_data["team"]
        if not user_can_manage_organization(self.request.user, team.organization):
            raise PermissionDenied("No puedes planificar sesiones para ese equipo.")
        messages.success(self.request, "Sesión planificada correctamente.")
        return super().form_valid(form)


class TrainingSessionUpdateView(LoginRequiredMixin, UpdateView):
    model = TrainingSession
    form_class = TrainingSessionForm
    template_name = "entrenamientos/form.html"
    success_url = reverse_lazy("training:session-list")
    extra_context = {"form_title": "Editar sesión"}

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        team = form.cleaned_data["team"]
        if not user_can_manage_organization(self.request.user, team.organization):
            raise PermissionDenied("No puedes modificar esa sesión.")
        messages.success(self.request, "Sesión actualizada correctamente.")
        return super().form_valid(form)