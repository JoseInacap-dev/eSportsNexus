import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from core.mixins import OrganizationAccessMixin, StaffRequiredMixin
from core.permissions import (
    user_can_manage_organization,
    user_can_view_organization,
)
from matches.brackets import (
    build_bracket,
    build_groups,
    build_standings,
    playoff_qualifiers,
)
from matches.forms import (
    MatchForm,
    TournamentForm,
    TournamentParticipantFormSet,
)
from matches.models import Match, Tournament
from organizations.models import Game, Team


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


class TournamentListView(LoginRequiredMixin, ListView):
    """Catálogo de torneos (entidad global, visible para usuarios autenticados)."""

    model = Tournament
    template_name = "torneos/lista.html"
    context_object_name = "torneos"
    paginate_by = 12

    def get_queryset(self):
        queryset = (
            Tournament.objects.select_related("game")
            .annotate(matches_count=Count("matches"))
            .order_by("name")
        )
        search = self.request.GET.get("q")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(game__name__icontains=search)
            )
        game_id = self.request.GET.get("juego")
        if game_id:
            queryset = queryset.filter(game_id=game_id)
        tournament_format = self.request.GET.get("formato")
        if tournament_format:
            queryset = queryset.filter(format=tournament_format)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["games"] = Game.objects.order_by("name")
        context["formats"] = Tournament.Format.choices
        context["can_manage"] = self.request.user.is_staff or self.request.user.is_superuser
        return context


class TournamentDetailView(LoginRequiredMixin, DetailView):
    model = Tournament
    template_name = "torneos/detalle.html"
    context_object_name = "torneo"

    def get_queryset(self):
        return Tournament.objects.select_related("game")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tournament = self.object
        context["partidos"] = tournament.matches.select_related(
            "game", "home_team", "away_team"
        ).order_by("-scheduled_at")
        context["participants"] = tournament.participants.select_related(
            "team", "team__organization"
        ).order_by("seed", "team__name")
        context["count_mismatch"] = tournament.has_participants_mismatch
        context["can_manage"] = self.request.user.is_staff or self.request.user.is_superuser

        tournament_format = tournament.format
        groups = []
        if tournament_format == Tournament.Format.GROUPS_PLAYOFFS:
            groups = build_groups(tournament)
            context["groups"] = groups
            context["bracket"] = build_bracket(
                tournament, teams=playoff_qualifiers(groups)
            )
        elif tournament_format in (
            Tournament.Format.ROUND_ROBIN,
            Tournament.Format.SWISS,
        ):
            context["standings"] = build_standings(tournament)
        elif tournament_format in (
            Tournament.Format.SINGLE_ELIMINATION,
            Tournament.Format.DOUBLE_ELIMINATION,
        ):
            context["bracket"] = build_bracket(tournament)
        return context


class TournamentCreateView(StaffRequiredMixin, CreateView):
    model = Tournament
    form_class = TournamentForm
    template_name = "torneos/form.html"
    extra_context = {"form_title": "Nuevo torneo"}

    def form_valid(self, form):
        response = super().form_valid(form)
        self._warn_mismatch()
        messages.success(self.request, "Torneo creado correctamente.")
        return response

    def _warn_mismatch(self):
        if self.object.has_participants_mismatch:
            messages.warning(
                self.request,
                "El número de participantes inscritos "
                f"({self.object.participants_total}) no coincide con el "
                f"especificado ({self.object.participants_count}).",
            )

    def get_success_url(self):
        return reverse("matches:tournament-detail", args=[self.object.pk])


class TournamentUpdateView(StaffRequiredMixin, UpdateView):
    model = Tournament
    form_class = TournamentForm
    template_name = "torneos/form.html"
    extra_context = {"form_title": "Editar torneo"}

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.object.has_participants_mismatch:
            messages.warning(
                self.request,
                "El número de participantes inscritos "
                f"({self.object.participants_total}) no coincide con el "
                f"especificado ({self.object.participants_count}).",
            )
        messages.success(self.request, "Torneo actualizado correctamente.")
        return response

    def get_success_url(self):
        return reverse("matches:tournament-detail", args=[self.object.pk])


class TournamentParticipantsView(StaffRequiredMixin, View):
    """Gestión manual de participantes: equipo, grupo y posición (seeds)."""

    template_name = "torneos/participantes_form.html"

    def _get_tournament(self, pk):
        return get_object_or_404(Tournament.objects.select_related("game"), pk=pk)

    def _formset(self, tournament, data=None):
        return TournamentParticipantFormSet(
            data=data,
            instance=tournament,
            form_kwargs={"tournament": tournament},
        )

    def get(self, request, pk):
        tournament = self._get_tournament(pk)
        formset = self._formset(tournament)
        return self._render(request, tournament, formset)

    def post(self, request, pk):
        tournament = self._get_tournament(pk)
        formset = self._formset(tournament, data=request.POST)
        if formset.is_valid():
            formset.save()
            if tournament.has_participants_mismatch:
                messages.warning(
                    request,
                    "El número de participantes inscritos "
                    f"({tournament.participants_total}) no coincide con el "
                    f"especificado ({tournament.participants_count}).",
                )
            messages.success(request, "Participantes actualizados correctamente.")
            return redirect("matches:tournament-detail", pk=tournament.pk)
        return self._render(request, tournament, formset)

    def _render(self, request, tournament, formset):
        return render(
            request,
            self.template_name,
            {
                "torneo": tournament,
                "formset": formset,
                "count_mismatch": tournament.has_participants_mismatch,
            },
        )


class TournamentDeleteView(StaffRequiredMixin, DeleteView):
    model = Tournament
    template_name = "confirmar_eliminar.html"
    success_url = reverse_lazy("matches:tournament-list")

    def form_valid(self, form):
        messages.success(self.request, "Torneo eliminado.")
        return super().form_valid(form)


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