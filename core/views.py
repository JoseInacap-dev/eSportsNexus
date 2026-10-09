from collections import OrderedDict
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.utils import timezone
from django.views.generic import TemplateView, View

from matches.models import Match
from organizations.models import Game, Organization, Team
from players.models import Player
from training.models import TrainingSession


def _winrate(matches):
    """Calcula el winrate (0-100) de un iterable de partidos finalizados."""
    played = 0
    wins = 0
    for home_score, away_score in matches:
        if home_score is None or away_score is None:
            continue
        played += 1
        if home_score > away_score:
            wins += 1
    return round(wins / played * 100, 1) if played else 0


class HomeView(TemplateView):
    """Página principal con un resumen general de la plataforma."""

    template_name = "home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        finished_scores = Match.objects.filter(
            status=Match.Status.FINISHED
        ).values_list("home_score", "away_score")

        context.update(
            total_equipos=Team.objects.count(),
            total_jugadores=Player.objects.count(),
            total_organizaciones=Organization.objects.count(),
            total_juegos=Game.objects.count(),
            partidos_mes=Match.objects.filter(scheduled_at__gte=month_start).count(),
            winrate_global=_winrate(finished_scores),
            proximos_partidos=Match.objects.filter(
                status=Match.Status.SCHEDULED, scheduled_at__gte=now
            )
            .select_related("game", "home_team", "away_team")
            .order_by("scheduled_at")[:5],
            resultados_recientes=Match.objects.filter(status=Match.Status.FINISHED)
            .select_related("game", "home_team", "away_team")
            .order_by("-scheduled_at")[:5],
            actividades=self._recent_activity(),
        )
        return context

    @staticmethod
    def _recent_activity():
        """Timeline sencillo construido a partir de los últimos registros."""
        activity = []
        for match in Match.objects.select_related("home_team").order_by(
            "-created_at"
        )[:3]:
            activity.append(
                {
                    "descripcion": f"Partido registrado: {match.home_team} vs {match.opponent}",
                    "fecha": match.created_at,
                    "usuario": "Staff",
                }
            )
        for session in TrainingSession.objects.select_related("team").order_by(
            "-created_at"
        )[:3]:
            activity.append(
                {
                    "descripcion": f"Sesión planificada: {session.title}",
                    "fecha": session.created_at,
                    "usuario": "Staff",
                }
            )
        activity.sort(key=lambda item: item["fecha"], reverse=True)
        return activity[:5]


class EstadisticasView(LoginRequiredMixin, TemplateView):
    """Centro de análisis: KPIs, evolución mensual y ranking de equipos."""

    template_name = "estadisticas/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()

        equipos = Team.objects.select_related("game", "organization").all()
        equipo_id = self.request.GET.get("equipo")
        if equipo_id:
            equipos = equipos.filter(pk=equipo_id)

        all_finished = Match.objects.filter(status=Match.Status.FINISHED)
        if equipo_id:
            all_finished = all_finished.filter(home_team_id=equipo_id)

        context.update(
            equipos=Team.objects.select_related("game").order_by("name"),
            kpis={
                "total_partidos": Match.objects.count(),
                "winrate_promedio": _winrate(
                    all_finished.values_list("home_score", "away_score")
                ),
                "total_entrenamientos": TrainingSession.objects.count(),
                "jugadores_activos": Player.objects.filter(
                    team_assignments__left_at__isnull=True
                )
                .distinct()
                .count(),
            },
            ranking_equipos=self._ranking(equipos),
            **self._evolution(all_finished, now),
        )
        return context

    @staticmethod
    def _ranking(equipos):
        ranking = []
        for team in equipos:
            scores = list(
                team.home_matches.filter(status=Match.Status.FINISHED).values_list(
                    "home_score", "away_score"
                )
            )
            played = [s for s in scores if s[0] is not None and s[1] is not None]
            wins = sum(1 for h, a in played if h > a)
            losses = len(played) - wins
            ranking.append(
                {
                    "nombre": team.name,
                    "juego": team.game.name,
                    "victorias": wins,
                    "derrotas": losses,
                    "winrate": round(wins / len(played) * 100, 1) if played else 0,
                }
            )
        ranking.sort(key=lambda item: item["winrate"], reverse=True)
        return ranking

    @staticmethod
    def _evolution(queryset, now):
        """Victorias/derrotas agrupadas por mes (últimos 6 meses)."""
        months = OrderedDict()
        for offset in range(5, -1, -1):
            first_day = (now.replace(day=1) - timedelta(days=offset * 30)).replace(
                day=1
            )
            key = first_day.strftime("%Y-%m")
            months[key] = {"label": first_day.strftime("%b"), "wins": 0, "losses": 0}

        for scheduled_at, home_score, away_score in queryset.values_list(
            "scheduled_at", "home_score", "away_score"
        ):
            key = scheduled_at.strftime("%Y-%m")
            if key not in months:
                continue
            if home_score is None or away_score is None:
                continue
            if home_score > away_score:
                months[key]["wins"] += 1
            elif away_score > home_score:
                months[key]["losses"] += 1

        return {
            "chart_meses": [data["label"] for data in months.values()],
            "chart_victorias": [data["wins"] for data in months.values()],
            "chart_derrotas": [data["losses"] for data in months.values()],
        }


class AjustesView(LoginRequiredMixin, TemplateView):
    """Ajustes generales de la plataforma (persistencia simulada por sesión)."""

    template_name = "configuracion/ajustes.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["configuracion"] = {
            "nombre_org": self.request.session.get("ajax_nombre_org", ""),
            "email_contacto": self.request.session.get("ajax_email_contacto", ""),
            "discord_webhook": self.request.session.get("ajax_discord_webhook", ""),
            "zona_horaria": self.request.session.get("ajax_zona_horaria", ""),
        }
        return context

    def post(self, request, *args, **kwargs):
        section = request.POST.get("seccion", "organizacion")
        request.session["ajax_nombre_org"] = request.POST.get("nombre_org", "")
        request.session["ajax_zona_horaria"] = request.POST.get("zona_horaria", "")
        request.session["ajax_email_contacto"] = request.POST.get("email_contacto", "")
        request.session["ajax_discord_webhook"] = request.POST.get("discord_webhook", "")
        messages.success(request, f"Configuración guardada ({section}).")
        return redirect("core:ajustes")
