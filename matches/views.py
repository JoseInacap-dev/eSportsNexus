import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from core.mixins import OrganizationAccessMixin
from core.permissions import (
    user_can_manage_organization,
    user_can_view_organization,
)
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
        user = self.request.user
        equipos = Team.objects.select_related("organization", "game").order_by(
            "name"
        )
        if not user.is_superuser:
            equipos = equipos.filter(
                organization__memberships__user=user,
                organization__memberships__is_active=True,
            ).distinct()
        context["equipos_disponibles"] = equipos
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
        context["can_manage"] = user_can_manage_organization(
            self.request.user, match.home_team.organization
        )
        context["statuses"] = Match.Status.choices
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


class MatchScoreView(LoginRequiredMixin, View):
    """Lectura y actualización en vivo del marcador de un partido (JSON).

    ``GET`` devuelve el marcador actual (para el auto-refresco del detalle).
    ``POST`` lo actualiza; requiere rol de gestión sobre la organización del
    equipo local. El resultado no se define al crear el partido: solo aquí.
    """

    def _get_match(self, pk):
        return get_object_or_404(
            Match.objects.select_related(
                "home_team", "home_team__organization", "away_team"
            ),
            pk=pk,
        )

    def _serialize(self, match):
        winner = match.winner
        return {
            "id": match.pk,
            "status": match.status,
            "status_display": match.get_status_display(),
            "home_score": match.home_score,
            "away_score": match.away_score,
            "is_live": match.is_live,
            "is_finished": match.is_finished,
            "has_score": match.has_score,
            "winner_id": winner.pk if winner else None,
            "home_team_id": match.home_team_id,
            "away_team_id": match.away_team_id,
        }

    def get(self, request, pk):
        match = self._get_match(pk)
        if not user_can_view_organization(request.user, match.home_team.organization):
            return JsonResponse(
                {"error": "No tienes acceso a este partido."}, status=403
            )
        return JsonResponse(self._serialize(match))

    def post(self, request, pk):
        match = self._get_match(pk)
        if not user_can_manage_organization(
            request.user, match.home_team.organization
        ):
            return JsonResponse(
                {"error": "No puedes actualizar este partido."}, status=403
            )

        try:
            payload = json.loads(request.body or b"{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "Cuerpo JSON inválido."}, status=400)

        valid_statuses = {value for value, _label in Match.Status.choices}
        status = payload.get("status", match.status)
        if status not in valid_statuses:
            return JsonResponse({"error": "Estado no válido."}, status=400)

        def parse_score(value):
            if value is None or value == "":
                return None
            try:
                score = int(value)
            except (TypeError, ValueError):
                raise ValueError("El marcador debe ser un número entero.")
            if score < 0:
                raise ValueError("El marcador no puede ser negativo.")
            return score

        try:
            home_score = parse_score(payload.get("home_score"))
            away_score = parse_score(payload.get("away_score"))
        except ValueError as exc:
            return JsonResponse({"error": str(exc)}, status=400)

        if status in (Match.Status.LIVE, Match.Status.FINISHED):
            home_score = 0 if home_score is None else home_score
            away_score = 0 if away_score is None else away_score

        match.status = status
        match.home_score = home_score
        match.away_score = away_score
        try:
            match.full_clean()
        except Exception as exc:  # ValidationError de constraint/estado
            return JsonResponse({"error": _validation_message(exc)}, status=400)
        match.save()
        return JsonResponse(self._serialize(match))


def _validation_message(exc):
    message_dict = getattr(exc, "message_dict", None)
    if message_dict:
        for messages_list in message_dict.values():
            if messages_list:
                return str(messages_list[0])
    messages_list = getattr(exc, "messages", None)
    if messages_list:
        return str(messages_list[0])
    return "No se pudo actualizar el marcador."