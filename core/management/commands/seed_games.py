"""Registra el catálogo de juegos competitivos.

Es idempotente: ejecutarlo varias veces no duplica registros.

Ejecución:
    python manage.py seed_games
"""

from django.core.management.base import BaseCommand

from organizations.models import Game

GAMES = [
    ("valorant", "Valorant", "VAL", 5),
    ("league-of-legends", "League of Legends", "LoL", 5),
    ("counter-strike-2", "Counter-Strike 2", "CS2", 5),
    ("dota-2", "Dota 2", "DOTA2", 5),
    ("overwatch", "Overwatch", "OW", 5),
    ("rocket-league", "Rocket League", "RL", 3),
    ("rainbow-six-siege", "Rainbow Six Siege", "R6", 5),
    ("fortnite", "Fortnite", "FN", 4),
    ("apex-legends", "Apex Legends", "APEX", 3),
    ("call-of-duty", "Call of Duty", "COD", 4),
    ("pubg", "PUBG", "PUBG", 4),
    ("pubg-mobile", "PUBG Mobile", "PUBGM", 4),
    ("wild-rift", "Wild Rift", "WR", 5),
    ("valorant-mobile", "Valorant Mobile", "VALM", 5),
    ("ea-sports-fc", "EA Sports FC", "FC", 1),
    ("starcraft-2", "StarCraft 2", "SC2", 1),
    ("mobile-legends", "Mobile Legends", "MLBB", 5),
]


class Command(BaseCommand):
    help = "Registra el catálogo de juegos competitivos (idempotente)"

    def handle(self, *args, **options):
        created = 0
        for slug, name, short_name, team_size in GAMES:
            _, was_created = Game.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "short_name": short_name,
                    "default_team_size": team_size,
                },
            )
            if was_created:
                created += 1
        total = Game.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f"[+] Juegos creados: {created}. Total en base de datos: {total}."
            )
        )
