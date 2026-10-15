from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.utils import timezone
from django.views.generic import TemplateView

from matches.models import Match
from organizations.models import Game, Organization, Team
from players.models import Player
from training.models import TrainingSession


class HomeView(TemplateView):
    """Página principal con un resumen general de la plataforma."""

    template_name = "home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        context.update(
            total_equipos=Team.objects.count(),
            total_jugadores=Player.objects.count(),
            total_organizaciones=Organization.objects.count(),
            total_juegos=Game.objects.count(),
            partidos_mes=Match.objects.filter(scheduled_at__gte=month_start).count(),
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
