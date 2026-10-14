"""Comando para poblar la base de datos con datos iniciales (seed data).

Ejecución:
    python manage.py seed_data
"""

import re
from datetime import date, datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import OrganizationMembership, User
from matches.models import Match, MatchMap, StatDefinition
from organizations.models import Game, GameRole, Organization, Team
from players.models import Player, PlayerTeamAssignment
from staff.models import StaffMember, TeamStaffAssignment
from training.models import TrainingAttendance, TrainingSession


# Catálogo de roles competitivos por juego (slug -> [(nombre, abreviatura), ...]).
# Los juegos 1v1 (EA Sports FC, StarCraft 2) no definen roles.
ROLES = {
    "valorant": [
        ("Duelist", "DUEL"),
        ("Initiator", "INIT"),
        ("Controller", "CTRL"),
        ("Sentinel", "SENT"),
        ("Flex", "FLEX"),
        ("Coach", "COACH"),
    ],
    "league-of-legends": [
        ("Top Laner", "TOP"),
        ("Jungler", "JNG"),
        ("Mid Laner", "MID"),
        ("ADC", "ADC"),
        ("Support", "SUPP"),
        ("Coach", "COACH"),
    ],
    "counter-strike-2": [
        ("Entry Fragger", "ENTRY"),
        ("AWPer", "AWP"),
        ("In-Game Leader", "IGL"),
        ("Lurker", "LURK"),
        ("Support", "SUPP"),
        ("Coach", "COACH"),
    ],
    "dota-2": [
        ("Carry", "CAR"),
        ("Mid", "MID"),
        ("Offlane", "OFF"),
        ("Soft Support", "S4"),
        ("Hard Support", "S5"),
        ("Coach", "COACH"),
    ],
    "overwatch": [
        ("Tank", "TANK"),
        ("Damage", "DPS"),
        ("Support", "SUPP"),
        ("Coach", "COACH"),
    ],
    "rocket-league": [
        ("Attacker", "ATK"),
        ("Midfielder", "MID"),
        ("Defender", "DEF"),
        ("Coach", "COACH"),
    ],
    "rainbow-six-siege": [
        ("Entry Fragger", "ENTRY"),
        ("Hard Breacher", "BREACH"),
        ("Support", "SUPP"),
        ("Flex", "FLEX"),
        ("Roamer", "ROAM"),
        ("Anchor", "ANCH"),
        ("Coach", "COACH"),
    ],
    "fortnite": [
        ("Fragger", "FRAG"),
        ("IGL", "IGL"),
        ("Support", "SUPP"),
        ("Builder", "BLD"),
        ("Coach", "COACH"),
    ],
    "apex-legends": [
        ("Assault", "ASSAULT"),
        ("Skirmisher", "SKIRM"),
        ("Recon", "RECON"),
        ("Controller", "CTRL"),
        ("Support", "SUPP"),
        ("Coach", "COACH"),
    ],
    "call-of-duty": [
        ("Slayer", "SLY"),
        ("Objective", "OBJ"),
        ("Flex", "FLEX"),
        ("Sniper", "SNP"),
        ("Coach", "COACH"),
    ],
    "pubg": [
        ("IGL", "IGL"),
        ("Fragger", "FRAG"),
        ("Support", "SUPP"),
        ("Scout", "SCT"),
        ("Coach", "COACH"),
    ],
    "pubg-mobile": [
        ("IGL", "IGL"),
        ("Fragger", "FRAG"),
        ("Support", "SUPP"),
        ("Sniper", "SNP"),
        ("Coach", "COACH"),
    ],
    "wild-rift": [
        ("Baron Laner", "BARON"),
        ("Jungler", "JNG"),
        ("Mid Laner", "MID"),
        ("Dragon Laner", "DRAGON"),
        ("Support", "SUPP"),
        ("Coach", "COACH"),
    ],
    "valorant-mobile": [
        ("Duelist", "DUEL"),
        ("Initiator", "INIT"),
        ("Controller", "CTRL"),
        ("Sentinel", "SENT"),
        ("Coach", "COACH"),
    ],
    "mobile-legends": [
        ("Tank", "TANK"),
        ("Fighter", "FIGHTER"),
        ("Assassin", "ASSASSIN"),
        ("Mage", "MAGE"),
        ("Marksman", "MM"),
        ("Support", "SUPP"),
        ("Coach", "COACH"),
    ],
}


# Organizaciones de esports reconocidas mundialmente. Algunas (G2, Fnatic)
# compiten en más de un juego, por lo que su org se reutiliza entre equipos.
PRO_ORGS = {
    "gen-g": {
        "name": "Gen.G Esports",
        "abbreviation": "GEN",
        "country": "Corea del Sur",
        "description": "Organización coreana con una de las plantillas más dominantes de la LCK.",
        "founded_date": date(2017, 5, 1),
        "website": "https://geng.gg",
    },
    "jd-gaming": {
        "name": "JD Gaming",
        "abbreviation": "JDG",
        "country": "China",
        "description": "Potencia de la LPL respaldada por JD.com y campeona de la LPL 2023.",
        "founded_date": date(2017, 3, 1),
        "website": "https://www.jdgaming.com",
    },
    "g2-esports": {
        "name": "G2 Esports",
        "abbreviation": "G2",
        "country": "Alemania",
        "description": "Club europeo multijuego con presencia en LoL, Valorant y más títulos.",
        "founded_date": date(2014, 2, 24),
        "website": "https://g2esports.com",
    },
    "fnatic": {
        "name": "Fnatic",
        "abbreviation": "FNC",
        "country": "Reino Unido",
        "description": "Una de las organizaciones más históricas de Europa y del mundo.",
        "founded_date": date(2004, 7, 23),
        "website": "https://fnatic.com",
    },
    "team-liquid": {
        "name": "Team Liquid",
        "abbreviation": "TL",
        "country": "Países Bajos",
        "description": "Organización neerlandesa con equipos en las principales ligas de esports.",
        "founded_date": date(2000, 1, 1),
        "website": "https://teamliquid.com",
    },
    "sentinels": {
        "name": "Sentinels",
        "abbreviation": "SEN",
        "country": "Estados Unidos",
        "description": "Ícono de Norteamérica en Valorant, campeón de Masters Reykjavík 2021.",
        "founded_date": date(2018, 3, 1),
        "website": "https://sentinels.gg",
    },
    "paper-rex": {
        "name": "Paper Rex",
        "abbreviation": "PRX",
        "country": "Singapur",
        "description": "Organización del Pacífico reconocida por su estilo de juego agresivo.",
        "founded_date": date(2020, 3, 1),
        "website": "https://paperrex.gg",
    },
    "loud": {
        "name": "LOUD",
        "abbreviation": "LOUD",
        "country": "Brasil",
        "description": "El club de esports más grande de Brasil y campeón de Champions 2022.",
        "founded_date": date(2019, 6, 1),
        "website": "https://loud.gg",
    },
}


# Equipos profesionales: 5 de League of Legends y 5 de Valorant. Cada uno con
# 5 titulares y 1 coach (asignación con rol competitivo "Coach").
PRO_TEAMS = [
    # --- League of Legends ---
    {
        "org": "gen-g",
        "game": "league-of-legends",
        "name": "Gen.G LoL",
        "description": "Roster de Gen.G en la LCK.",
        "founded_date": date(2017, 5, 1),
        "players": [
            ("Kim", "Gi-in", "Kiin", "Corea del Sur", "Top Laner", False),
            ("Kim", "Geon-bu", "Canyon", "Corea del Sur", "Jungler", False),
            ("Jeong", "Ji-hun", "Chovy", "Corea del Sur", "Mid Laner", True),
            ("Kim", "Su-hwan", "Peyz", "Corea del Sur", "ADC", False),
            ("Son", "Si-woo", "Lehends", "Corea del Sur", "Support", False),
        ],
        "coach": ("Kim", "Jeong-soo", "Kim", "Corea del Sur"),
    },
    {
        "org": "jd-gaming",
        "game": "league-of-legends",
        "name": "JD Gaming LoL",
        "description": "Roster de JD Gaming en la LPL.",
        "founded_date": date(2017, 3, 1),
        "players": [
            ("Bai", "Jia-Hao", "369", "China", "Top Laner", False),
            ("Seo", "Jin-hyeok", "Kanavi", "Corea del Sur", "Jungler", True),
            ("Zhuo", "Ding", "Knight", "China", "Mid Laner", False),
            ("Park", "Jae-hyuk", "Ruler", "Corea del Sur", "ADC", False),
            ("Lou", "Yun-Feng", "Missing", "China", "Support", False),
        ],
        "coach": ("Yoon", "Sung-young", "Homme", "Corea del Sur"),
    },
    {
        "org": "g2-esports",
        "game": "league-of-legends",
        "name": "G2 Esports LoL",
        "description": "Roster de G2 Esports en la LEC.",
        "founded_date": date(2014, 2, 24),
        "players": [
            ("Sergen", "Çelik", "Broken Blade", "Turquía", "Top Laner", False),
            ("Martin", "Sundelin", "Yike", "Suecia", "Jungler", False),
            ("Rasmus", "Winther", "Caps", "Dinamarca", "Mid Laner", True),
            ("Steven", "Liv", "Hans Sama", "Francia", "ADC", False),
            ("Mihael", "Mehle", "Mikyx", "Eslovenia", "Support", False),
        ],
        "coach": ("Dylan", "Falco", "Dylan", "Estados Unidos"),
    },
    {
        "org": "fnatic",
        "game": "league-of-legends",
        "name": "Fnatic LoL",
        "description": "Roster de Fnatic en la LEC.",
        "founded_date": date(2004, 7, 23),
        "players": [
            ("Óscar", "Muñoz", "Oscarinin", "España", "Top Laner", False),
            ("Iván", "Martín", "Razork", "España", "Jungler", False),
            ("Marek", "Brázda", "Humanoid", "Chequia", "Mid Laner", True),
            ("Oh", "Hyeon-taek", "Noah", "Corea del Sur", "ADC", False),
            ("Yoon", "Se-jun", "Jun", "Corea del Sur", "Support", False),
        ],
        "coach": ("Aleš", "Kněžínek", "Nightshare", "Chequia"),
    },
    {
        "org": "team-liquid",
        "game": "league-of-legends",
        "name": "Team Liquid LoL",
        "description": "Roster de Team Liquid en la LCS.",
        "founded_date": date(2000, 1, 1),
        "players": [
            ("Jung", "Eon-young", "Impact", "Corea del Sur", "Top Laner", False),
            ("Eom", "Sung-hyeon", "UmTi", "Corea del Sur", "Jungler", False),
            ("Eain", "Stearns", "APA", "Estados Unidos", "Mid Laner", False),
            ("Sean", "Sung", "Yeon", "Estados Unidos", "ADC", False),
            ("Jo", "Yong-in", "CoreJJ", "Corea del Sur", "Support", True),
        ],
        "coach": ("Jang", "Dae-woong", "Spawn", "Corea del Sur"),
    },
    # --- Valorant ---
    {
        "org": "sentinels",
        "game": "valorant",
        "name": "Sentinels Valorant",
        "description": "Roster de Sentinels en el VCT Americas.",
        "founded_date": date(2018, 3, 1),
        "players": [
            ("Tyson", "Ngo", "TenZ", "Canadá", "Duelist", False),
            ("Zachary", "Patrone", "zekken", "Estados Unidos", "Duelist", False),
            ("Gustavo", "Rossi", "Sacy", "Brasil", "Initiator", False),
            ("Bryan", "Luna", "pANcada", "Brasil", "Controller", False),
            ("Mouhamed", "Ouarid", "johnqt", "Marruecos", "Sentinel", True),
        ],
        "coach": ("Adam", "Kaplan", "Kaplan", "Estados Unidos"),
    },
    {
        "org": "paper-rex",
        "game": "valorant",
        "name": "Paper Rex Valorant",
        "description": "Roster de Paper Rex en el VCT Pacific.",
        "founded_date": date(2020, 3, 1),
        "players": [
            ("Jason", "Susanto", "f0rsakeN", "Indonesia", "Controller", True),
            ("Wang", "Jing Jie", "Jinggg", "Singapur", "Duelist", False),
            ("Khalish", "Rusyaidee", "d4v41", "Malasia", "Initiator", False),
            ("Ilya", "Petrov", "something", "Rusia", "Duelist", False),
            ("Aaron", "Leonhart", "mindfreak", "Indonesia", "Sentinel", False),
        ],
        "coach": ("Alexandre", "Sallé", "alecks", "Francia"),
    },
    {
        "org": "loud",
        "game": "valorant",
        "name": "LOUD Valorant",
        "description": "Roster de LOUD en el VCT Americas.",
        "founded_date": date(2019, 6, 1),
        "players": [
            ("Erick", "Santos", "aspas", "Brasil", "Duelist", False),
            ("Matias", "Delipetro", "saadhak", "Argentina", "Initiator", True),
            ("Felipe", "Basso", "less", "Brasil", "Sentinel", False),
            ("Arthur", "Andrade", "tuyz", "Brasil", "Controller", False),
            ("Gabriel", "Cavalcanti", "cauanzin", "Brasil", "Flex", False),
        ],
        "coach": ("Rodrigo", "Rocha", "bzkA", "Brasil"),
    },
    {
        "org": "fnatic",
        "game": "valorant",
        "name": "Fnatic Valorant",
        "description": "Roster de Fnatic en el VCT EMEA.",
        "founded_date": date(2004, 7, 23),
        "players": [
            ("Jake", "Howlett", "Boaster", "Reino Unido", "Controller", True),
            ("Nikita", "Sirmitev", "Derke", "Finlandia", "Duelist", False),
            ("Emir", "Beder", "Alfajer", "Turquía", "Sentinel", False),
            ("Timofey", "Khromov", "Chronicle", "Rusia", "Flex", False),
            ("Leo", "Jannesson", "Leo", "Suecia", "Initiator", False),
        ],
        "coach": ("Jacob", "Harris", "mini", "Reino Unido"),
    },
    {
        "org": "g2-esports",
        "game": "valorant",
        "name": "G2 Esports Valorant",
        "description": "Roster de G2 Esports en el VCT EMEA.",
        "founded_date": date(2014, 2, 24),
        "players": [
            ("Jacob", "Batio", "valyn", "Estados Unidos", "Controller", True),
            ("Trent", "Cairns", "trent", "Estados Unidos", "Initiator", False),
            ("Jonah", "Pulice", "JonahP", "Estados Unidos", "Duelist", False),
            ("Nathan", "Orf", "leaf", "Estados Unidos", "Flex", False),
            ("Jacob", "Lange", "icy", "Estados Unidos", "Sentinel", False),
        ],
        "coach": ("Daniel", "Sores", "d00mbr0s", "Israel"),
    },
]


# Enfrentamientos entre equipos del mismo juego (10 de LoL + 10 de Valorant).
# Fechas fijas para que el comando sea idempotente. T1 y LBF son equipos del
# usuario: si no existen, sus partidos se omiten sin error.
PRO_MATCHES = [
    # --- League of Legends ---
    {
        "home": "Gen.G LoL",
        "away": "T1",
        "game": "league-of-legends",
        "kind": Match.Kind.OFFICIAL,
        "status": Match.Status.FINISHED,
        "tournament": "LCK 2026 Verano",
        "best_of": 3,
        "home_score": 2,
        "away_score": 1,
        "scheduled_at": datetime(2026, 9, 5, 18, 0),
    },
    {
        "home": "JD Gaming LoL",
        "away": "Team Liquid LoL",
        "game": "league-of-legends",
        "kind": Match.Kind.TOURNAMENT,
        "status": Match.Status.FINISHED,
        "tournament": "Rift Rivals 2026",
        "best_of": 3,
        "home_score": 2,
        "away_score": 0,
        "scheduled_at": datetime(2026, 9, 8, 20, 0),
    },
    {
        "home": "G2 Esports LoL",
        "away": "Fnatic LoL",
        "game": "league-of-legends",
        "kind": Match.Kind.OFFICIAL,
        "status": Match.Status.FINISHED,
        "tournament": "LEC 2026 Summer Playoffs",
        "best_of": 5,
        "home_score": 3,
        "away_score": 2,
        "scheduled_at": datetime(2026, 9, 12, 19, 0),
    },
    {
        "home": "Fnatic LoL",
        "away": "Gen.G LoL",
        "game": "league-of-legends",
        "kind": Match.Kind.TOURNAMENT,
        "status": Match.Status.FINISHED,
        "tournament": "Worlds 2026 Grupos",
        "best_of": 3,
        "home_score": 0,
        "away_score": 2,
        "scheduled_at": datetime(2026, 9, 18, 17, 0),
    },
    {
        "home": "Team Liquid LoL",
        "away": "T1",
        "game": "league-of-legends",
        "kind": Match.Kind.FRIENDLY,
        "status": Match.Status.FINISHED,
        "tournament": "Showmatch",
        "best_of": 1,
        "home_score": 0,
        "away_score": 1,
        "scheduled_at": datetime(2026, 9, 25, 21, 0),
    },
    {
        "home": "G2 Esports LoL",
        "away": "JD Gaming LoL",
        "game": "league-of-legends",
        "kind": Match.Kind.SCRIM,
        "status": Match.Status.FINISHED,
        "tournament": "Scrim Block A",
        "best_of": 3,
        "home_score": 1,
        "away_score": 2,
        "scheduled_at": datetime(2026, 10, 2, 19, 30),
    },
    {
        "home": "Gen.G LoL",
        "away": "JD Gaming LoL",
        "game": "league-of-legends",
        "kind": Match.Kind.TOURNAMENT,
        "status": Match.Status.SCHEDULED,
        "tournament": "Worlds 2026 Semifinal",
        "best_of": 5,
        "scheduled_at": datetime(2026, 11, 7, 18, 0),
    },
    {
        "home": "T1",
        "away": "Fnatic LoL",
        "game": "league-of-legends",
        "kind": Match.Kind.TOURNAMENT,
        "status": Match.Status.SCHEDULED,
        "tournament": "Mundial 2026",
        "best_of": 3,
        "scheduled_at": datetime(2026, 11, 14, 20, 0),
    },
    {
        "home": "Team Liquid LoL",
        "away": "G2 Esports LoL",
        "game": "league-of-legends",
        "kind": Match.Kind.OFFICIAL,
        "status": Match.Status.SCHEDULED,
        "tournament": "LCS vs LEC",
        "best_of": 3,
        "scheduled_at": datetime(2026, 11, 21, 19, 0),
    },
    {
        "home": "Fnatic LoL",
        "away": "Team Liquid LoL",
        "game": "league-of-legends",
        "kind": Match.Kind.OFFICIAL,
        "status": Match.Status.SCHEDULED,
        "tournament": "LEC 2026 Winter",
        "best_of": 1,
        "scheduled_at": datetime(2026, 12, 5, 18, 30),
    },
    # --- Valorant ---
    {
        "home": "Sentinels Valorant",
        "away": "LOUD Valorant",
        "game": "valorant",
        "kind": Match.Kind.TOURNAMENT,
        "status": Match.Status.FINISHED,
        "tournament": "VCT Americas 2026 Stage 2",
        "best_of": 3,
        "home_score": 2,
        "away_score": 1,
        "scheduled_at": datetime(2026, 9, 6, 18, 0),
        "maps": [
            ("Haven", 13, 9, MatchMap.Outcome.HOME),
            ("Ascent", 10, 13, MatchMap.Outcome.AWAY),
            ("Lotus", 13, 11, MatchMap.Outcome.HOME),
        ],
    },
    {
        "home": "Paper Rex Valorant",
        "away": "G2 Esports Valorant",
        "game": "valorant",
        "kind": Match.Kind.TOURNAMENT,
        "status": Match.Status.FINISHED,
        "tournament": "VCT Masters 2026",
        "best_of": 3,
        "home_score": 2,
        "away_score": 0,
        "scheduled_at": datetime(2026, 9, 10, 20, 0),
        "maps": [
            ("Split", 13, 7, MatchMap.Outcome.HOME),
            ("Bind", 13, 10, MatchMap.Outcome.HOME),
        ],
    },
    {
        "home": "Fnatic Valorant",
        "away": "Sentinels Valorant",
        "game": "valorant",
        "kind": Match.Kind.OFFICIAL,
        "status": Match.Status.FINISHED,
        "tournament": "VCT EMEA 2026",
        "best_of": 3,
        "home_score": 1,
        "away_score": 2,
        "scheduled_at": datetime(2026, 9, 15, 19, 0),
        "maps": [
            ("Icebox", 8, 13, MatchMap.Outcome.AWAY),
            ("Ascent", 13, 11, MatchMap.Outcome.HOME),
            ("Sunset", 11, 13, MatchMap.Outcome.AWAY),
        ],
    },
    {
        "home": "LOUD Valorant",
        "away": "LBF",
        "game": "valorant",
        "kind": Match.Kind.FRIENDLY,
        "status": Match.Status.FINISHED,
        "tournament": "Amistoso internacional",
        "best_of": 1,
        "home_score": 1,
        "away_score": 0,
        "scheduled_at": datetime(2026, 9, 22, 21, 0),
    },
    {
        "home": "G2 Esports Valorant",
        "away": "Fnatic Valorant",
        "game": "valorant",
        "kind": Match.Kind.OFFICIAL,
        "status": Match.Status.FINISHED,
        "tournament": "VCT EMEA 2026 Playoffs",
        "best_of": 5,
        "home_score": 2,
        "away_score": 3,
        "scheduled_at": datetime(2026, 9, 29, 19, 0),
    },
    {
        "home": "LBF",
        "away": "Paper Rex Valorant",
        "game": "valorant",
        "kind": Match.Kind.SCRIM,
        "status": Match.Status.FINISHED,
        "tournament": "Scrim Block B",
        "best_of": 3,
        "home_score": 0,
        "away_score": 2,
        "scheduled_at": datetime(2026, 10, 6, 20, 0),
    },
    {
        "home": "Sentinels Valorant",
        "away": "Paper Rex Valorant",
        "game": "valorant",
        "kind": Match.Kind.TOURNAMENT,
        "status": Match.Status.SCHEDULED,
        "tournament": "Valorant Champions 2026",
        "best_of": 5,
        "scheduled_at": datetime(2026, 11, 8, 19, 0),
    },
    {
        "home": "Fnatic Valorant",
        "away": "LOUD Valorant",
        "game": "valorant",
        "kind": Match.Kind.TOURNAMENT,
        "status": Match.Status.SCHEDULED,
        "tournament": "Champions 2026 Grupos",
        "best_of": 3,
        "scheduled_at": datetime(2026, 11, 15, 20, 0),
    },
    {
        "home": "G2 Esports Valorant",
        "away": "LBF",
        "game": "valorant",
        "kind": Match.Kind.FRIENDLY,
        "status": Match.Status.SCHEDULED,
        "tournament": "Amistoso",
        "best_of": 1,
        "scheduled_at": datetime(2026, 11, 22, 18, 0),
    },
    {
        "home": "LOUD Valorant",
        "away": "Sentinels Valorant",
        "game": "valorant",
        "kind": Match.Kind.TOURNAMENT,
        "status": Match.Status.SCHEDULED,
        "tournament": "Champions 2026 Semifinal",
        "best_of": 5,
        "scheduled_at": datetime(2026, 12, 6, 19, 0),
    },
]


class Command(BaseCommand):
    help = "Puebla la base de datos con datos de prueba realistas para NEXUS Esports"

    def add_arguments(self, parser):
        parser.add_argument(
            "--only-roles",
            action="store_true",
            help="Crea únicamente los roles competitivos, sin datos demo.",
        )
        parser.add_argument(
            "--pro-teams",
            action="store_true",
            help=(
                "Crea únicamente los 10 equipos profesionales (5 LoL + 5 "
                "Valorant) con sus plantillas y coaches, sin datos demo."
            ),
        )
        parser.add_argument(
            "--pro-matches",
            action="store_true",
            help=(
                "Crea 20 partidos entre equipos del mismo juego (10 LoL + 10 "
                "Valorant). Garantiza antes los equipos profesionales."
            ),
        )

    def _seed_roles(self, games):
        created_roles = {}
        total_roles = 0
        for slug, roles in ROLES.items():
            game = games.get(slug)
            if game is None:
                continue
            for name, abbr in roles:
                role, _ = GameRole.objects.get_or_create(
                    game=game,
                    name=name,
                    defaults={"abbreviation": abbr},
                )
                created_roles[(slug, name)] = role
                total_roles += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"  [+] {total_roles} roles competitivos configurados"
            )
        )
        return created_roles

    @staticmethod
    def _pro_email(nickname, org_slug):
        handle = re.sub(r"[^a-z0-9]", "", nickname.lower())
        return f"{handle}@{org_slug}.gg"

    def _pro_games(self):
        """Asegura la existencia de los juegos usados por los equipos pro."""
        metas = {
            "valorant": ("Valorant", "VAL", 5),
            "league-of-legends": ("League of Legends", "LoL", 5),
        }
        games = {}
        for slug, (name, short_name, team_size) in metas.items():
            game, _ = Game.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "short_name": short_name,
                    "default_team_size": team_size,
                },
            )
            games[slug] = game
        return games

    def _get_role(self, game, role_name):
        abbreviation = dict(ROLES.get(game.slug, [])).get(role_name, "")
        role, _ = GameRole.objects.get_or_create(
            game=game,
            name=role_name,
            defaults={"abbreviation": abbreviation},
        )
        return role

    def _seed_pro_teams(self):
        games = self._pro_games()

        orgs = {}
        for slug, data in PRO_ORGS.items():
            org, _ = Organization.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": data["name"],
                    "abbreviation": data["abbreviation"],
                    "country": data["country"],
                    "description": data["description"],
                    "founded_date": data["founded_date"],
                    "website": data["website"],
                },
            )
            orgs[slug] = org

        # Vincula a los usuarios existentes para que los equipos sean visibles
        # en la UI con scoping por membresía (además de para superusuarios).
        users = list(User.objects.filter(is_active=True))
        for org in orgs.values():
            for user in users:
                OrganizationMembership.objects.get_or_create(
                    user=user,
                    organization=org,
                    defaults={
                        "role": OrganizationMembership.Role.OWNER,
                        "is_active": True,
                    },
                )

        total_players = 0
        for data in PRO_TEAMS:
            org = orgs[data["org"]]
            game = games[data["game"]]
            team, _ = Team.objects.get_or_create(
                organization=org,
                game=game,
                name=data["name"],
                defaults={
                    "description": data["description"],
                    "status": Team.Status.ACTIVE,
                    "founded_date": data["founded_date"],
                },
            )
            coach = data["coach"]
            roster = list(data["players"]) + [
                (coach[0], coach[1], coach[2], coach[3], "Coach", False)
            ]
            for fn, ln, nick, country, role_name, is_cap in roster:
                player, _ = Player.objects.get_or_create(
                    nickname=nick,
                    defaults={
                        "first_name": fn,
                        "last_name": ln,
                        "email": self._pro_email(nick, org.slug),
                        "country": country,
                        "birth_date": date(2000, 1, 1),
                    },
                )
                PlayerTeamAssignment.objects.get_or_create(
                    player=player,
                    team=team,
                    defaults={
                        "competitive_role": self._get_role(game, role_name),
                        "joined_at": date(2025, 1, 10),
                        "is_captain": is_cap,
                        "status": PlayerTeamAssignment.Status.ACTIVE,
                    },
                )
                total_players += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"  [+] {len(PRO_TEAMS)} equipos profesionales y "
                f"{total_players} jugadores/coaches registrados"
            )
        )

    def _pro_matches_teams(self):
        """Resuelve los equipos de los partidos pro por nombre.

        Garantiza primero los 10 equipos profesionales. T1 y LBF son equipos
        del usuario: si no existen, simplemente se omiten sus enfrentamientos.
        """
        self._seed_pro_teams()
        names = set()
        for data in PRO_MATCHES:
            names.add(data["home"])
            names.add(data["away"])
        teams = {team.name: team for team in Team.objects.filter(name__in=names)}

        # Los equipos del usuario pueden tener otro nombre (p. ej. "T1 LoL"),
        # así que se resuelven por organización + juego como respaldo.
        aliases = {
            "T1": ("t1", "league-of-legends"),
            "LBF": ("low-battery-five", "valorant"),
        }
        for key, (org_slug, game_slug) in aliases.items():
            if key in names and key not in teams:
                team = Team.objects.filter(
                    organization__slug=org_slug, game__slug=game_slug
                ).first()
                if team is not None:
                    teams[key] = team
        return teams

    def _seed_pro_matches(self):
        teams = self._pro_matches_teams()
        tz = timezone.get_current_timezone()
        created_matches = 0
        skipped = 0
        for data in PRO_MATCHES:
            home = teams.get(data["home"])
            away = teams.get(data["away"])
            if home is None or away is None:
                skipped += 1
                continue
            scheduled_at = timezone.make_aware(data["scheduled_at"], tz)
            match, created = Match.objects.get_or_create(
                home_team=home,
                away_team=away,
                scheduled_at=scheduled_at,
                defaults={
                    "game": home.game,
                    "kind": data["kind"],
                    "status": data["status"],
                    "tournament_name": data["tournament"],
                    "best_of": data["best_of"],
                    "home_score": data.get("home_score"),
                    "away_score": data.get("away_score"),
                },
            )
            if created:
                created_matches += 1
            for order, (map_name, hs, aws, outcome) in enumerate(
                data.get("maps", []), start=1
            ):
                MatchMap.objects.get_or_create(
                    match=match,
                    order=order,
                    defaults={
                        "map_name": map_name,
                        "home_score": hs,
                        "away_score": aws,
                        "outcome": outcome,
                    },
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"  [+] {created_matches} partidos creados "
                f"({len(PRO_MATCHES) - skipped} en total, {skipped} omitidos "
                "por equipos ausentes)"
            )
        )

    def handle(self, *args, **options):
        if options.get("only_roles"):
            games = {game.slug: game for game in Game.objects.all()}
            self.stdout.write(
                self.style.NOTICE("Creando únicamente roles competitivos...")
            )
            self._seed_roles(games)
            return

        if options.get("pro_teams"):
            self.stdout.write(
                self.style.NOTICE(
                    "Registrando equipos profesionales (LoL y Valorant)..."
                )
            )
            self._seed_pro_teams()
            return

        if options.get("pro_matches"):
            self.stdout.write(
                self.style.NOTICE(
                    "Registrando partidos entre equipos del mismo juego..."
                )
            )
            self._seed_pro_matches()
            return

        self.stdout.write(self.style.NOTICE("Iniciando inserción de datos de prueba..."))

        # 1. Superusuario y usuarios de prueba
        admin_user, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@nexusesports.com",
                "display_name": "Administrador General",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if created:
            admin_user.set_password("Nexus2026")
            admin_user.save()
            self.stdout.write(self.style.SUCCESS("  [+] Superusuario 'admin' creado (password: Nexus2026)"))
        else:
            self.stdout.write("  [*] Superusuario 'admin' ya existía")

        coach_user, _ = User.objects.get_or_create(
            username="coach_marcelo",
            defaults={
                "email": "marcelo@nexusesports.com",
                "display_name": "Marcelo 'Cortex' Díaz",
            },
        )
        coach_user.set_password("Nexus2026")
        coach_user.save()

        # 2. Juegos Competitivos
        games_data = [
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
        games = {}
        for slug, name, short_name, team_size in games_data:
            game, _ = Game.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "short_name": short_name,
                    "default_team_size": team_size,
                },
            )
            games[slug] = game
        val = games["valorant"]
        lol = games["league-of-legends"]
        cs2 = games["counter-strike-2"]
        self.stdout.write(
            self.style.SUCCESS(f"  [+] {len(games_data)} juegos competitivos registrados")
        )

        # 3. Roles por Juego
        created_roles = self._seed_roles(games)

        # 4. Organizaciones
        nexus_org, _ = Organization.objects.get_or_create(
            slug="nexus-esports",
            defaults={
                "name": "NEXUS Esports",
                "abbreviation": "NXS",
                "country": "Chile",
                "description": "Organización competitiva líder en la escena regional de esports.",
                "founded_date": date(2023, 1, 15),
            },
        )
        kru_org, _ = Organization.objects.get_or_create(
            slug="kru-esports",
            defaults={
                "name": "KRÜ Esports",
                "abbreviation": "KRU",
                "country": "Argentina",
                "description": "Club de esports fundado por Sergio Agüero.",
                "founded_date": date(2020, 10, 21),
            },
        )
        lev_org, _ = Organization.objects.get_or_create(
            slug="leviatan",
            defaults={
                "name": "Leviatán",
                "abbreviation": "LEV",
                "country": "Argentina",
                "description": "Organización internacional con presencia en VCT y LLA.",
                "founded_date": date(2020, 11, 1),
            },
        )

        # Vincular a todos los usuarios a NEXUS como Owner
        for u in User.objects.all():
            m, _ = OrganizationMembership.objects.get_or_create(
                user=u,
                organization=nexus_org,
                defaults={"role": OrganizationMembership.Role.OWNER, "is_active": True},
            )
            m.role = OrganizationMembership.Role.OWNER
            m.is_active = True
            m.save()

        # 5. Equipos
        team_nxs_val, _ = Team.objects.get_or_create(
            organization=nexus_org,
            name="NEXUS Valorant",
            defaults={
                "game": val,
                "description": "Escuadra principal de Valorant participando en VCT Challengers.",
                "status": Team.Status.ACTIVE,
                "founded_date": date(2023, 3, 1),
            },
        )
        team_nxs_lol, _ = Team.objects.get_or_create(
            organization=nexus_org,
            name="NEXUS League of Legends",
            defaults={
                "game": lol,
                "description": "Equipo competitivo de LoL en la Liga Regional Sur.",
                "status": Team.Status.ACTIVE,
                "founded_date": date(2023, 4, 1),
            },
        )
        team_nxs_cs2, _ = Team.objects.get_or_create(
            organization=nexus_org,
            name="NEXUS CS2",
            defaults={
                "game": cs2,
                "description": "Escuadra de Counter-Strike 2 en el circuito sudamericano.",
                "status": Team.Status.ACTIVE,
                "founded_date": date(2024, 1, 10),
            },
        )

        team_kru_val, _ = Team.objects.get_or_create(
            organization=kru_org,
            name="KRÜ Valorant",
            defaults={
                "game": val,
                "description": "Equipo oficial de Valorant de KRÜ.",
                "status": Team.Status.ACTIVE,
            },
        )
        team_lev_lol, _ = Team.objects.get_or_create(
            organization=lev_org,
            name="Leviatán LoL",
            defaults={
                "game": lol,
                "description": "Escuadra de League of Legends de Leviatán.",
                "status": Team.Status.ACTIVE,
            },
        )
        self.stdout.write(self.style.SUCCESS("  [+] Equipos creados: NEXUS VAL, NEXUS LoL, NEXUS CS2 y rivales"))

        # 6. Jugadores y Asignaciones
        players_data = [
            # NEXUS Valorant
            ("Matías", "Silva", "Tenzin", "matias.silva@nexus.gg", "Chile", team_nxs_val, ("valorant", "Duelist"), False),
            ("Carlos", "Vega", "Shadow", "carlos.vega@nexus.gg", "Chile", team_nxs_val, ("valorant", "Controller"), False),
            ("Ignacio", "Morales", "ViperX", "ignacio.m@nexus.gg", "Chile", team_nxs_val, ("valorant", "Sentinel"), True),
            ("Sebastián", "Soto", "Blaze", "sebastian.soto@nexus.gg", "Chile", team_nxs_val, ("valorant", "Initiator"), False),
            ("Felipe", "Castro", "Krono", "felipe.castro@nexus.gg", "Chile", team_nxs_val, ("valorant", "Initiator"), False),
            # NEXUS LoL
            ("Lucas", "Gómez", "Mythic", "lucas.gomez@nexus.gg", "Chile", team_nxs_lol, ("league-of-legends", "Top Laner"), False),
            ("Andrés", "Torres", "Ghost", "andres.torres@nexus.gg", "Argentina", team_nxs_lol, ("league-of-legends", "Jungler"), False),
            ("Joaquín", "Rivas", "Arcane", "joaquin.rivas@nexus.gg", "Chile", team_nxs_lol, ("league-of-legends", "Mid Laner"), True),
            ("Diego", "Araya", "Bullet", "diego.araya@nexus.gg", "Chile", team_nxs_lol, ("league-of-legends", "ADC"), False),
            ("Gonzalo", "Peña", "Oracle", "gonzalo.pena@nexus.gg", "Perú", team_nxs_lol, ("league-of-legends", "Support"), False),
            # NEXUS CS2
            ("Tomás", "Vargas", "Striker", "tomas.vargas@nexus.gg", "Chile", team_nxs_cs2, ("counter-strike-2", "Entry Fragger"), False),
            ("Rodrigo", "Muñoz", "SniperCL", "rodrigo.m@nexus.gg", "Chile", team_nxs_cs2, ("counter-strike-2", "AWPer"), False),
            ("Gabriel", "Ortiz", "MasterMind", "gabriel.ortiz@nexus.gg", "Chile", team_nxs_cs2, ("counter-strike-2", "In-Game Leader"), True),
            ("Cristóbal", "Herrera", "Smoke", "cristobal.h@nexus.gg", "Chile", team_nxs_cs2, ("counter-strike-2", "Lurker"), False),
            ("Esteban", "Rojas", "Anchor", "esteban.rojas@nexus.gg", "Chile", team_nxs_cs2, ("counter-strike-2", "Support"), False),
        ]

        assigned_players = []
        for fn, ln, nick, email, country, team, role_key, is_cap in players_data:
            p, _ = Player.objects.get_or_create(
                nickname=nick,
                defaults={
                    "first_name": fn,
                    "last_name": ln,
                    "email": email,
                    "country": country,
                    "birth_date": date(2002, 5, 20),
                },
            )
            role = created_roles.get(role_key)
            PlayerTeamAssignment.objects.get_or_create(
                player=p,
                team=team,
                defaults={
                    "competitive_role": role,
                    "joined_at": date(2025, 1, 10),
                    "is_captain": is_cap,
                    "status": PlayerTeamAssignment.Status.ACTIVE,
                },
            )
            assigned_players.append(p)
        self.stdout.write(self.style.SUCCESS(f"  [+] {len(players_data)} Jugadores registrados y asignados a sus plantillas"))

        # 7. Staff Técnico
        staff_1, _ = StaffMember.objects.get_or_create(
            email="marcelo.diaz@nexus.gg",
            defaults={"first_name": "Marcelo", "last_name": "Díaz", "country": "Chile"},
        )
        TeamStaffAssignment.objects.get_or_create(
            staff=staff_1,
            team=team_nxs_val,
            defaults={
                "role": TeamStaffAssignment.Role.HEAD_COACH,
                "started_at": date(2024, 2, 1),
            },
        )

        staff_2, _ = StaffMember.objects.get_or_create(
            email="fernando.lagos@nexus.gg",
            defaults={"first_name": "Fernando", "last_name": "Lagos", "country": "Chile"},
        )
        TeamStaffAssignment.objects.get_or_create(
            staff=staff_2,
            team=team_nxs_lol,
            defaults={
                "role": TeamStaffAssignment.Role.HEAD_COACH,
                "started_at": date(2024, 3, 1),
            },
        )
        self.stdout.write(self.style.SUCCESS("  [+] Staff técnico y entrenadores asignados"))

        # 8. Definición de Estadísticas
        StatDefinition.objects.get_or_create(
            game=val,
            scope=StatDefinition.Scope.PLAYER,
            code="kills",
            defaults={"name": "Kills", "unit": "bajas", "higher_is_better": True},
        )
        StatDefinition.objects.get_or_create(
            game=val,
            scope=StatDefinition.Scope.PLAYER,
            code="acs",
            defaults={"name": "Combat Score", "unit": "pts", "higher_is_better": True},
        )
        StatDefinition.objects.get_or_create(
            game=lol,
            scope=StatDefinition.Scope.PLAYER,
            code="kda",
            defaults={"name": "KDA Ratio", "unit": "ratio", "higher_is_better": True},
        )

        # 9. Partidos (Finalizados y Próximos)
        now = timezone.now()

        # Organización y equipos rivales (ambos bandos deben estar registrados).
        rival_org, _ = Organization.objects.get_or_create(
            slug="rivales",
            defaults={
                "name": "Rivales Esports",
                "abbreviation": "RIV",
                "country": "Internacional",
                "description": "Organización con equipos rivales de demostración.",
            },
        )
        rival_9z_cs2, _ = Team.objects.get_or_create(
            organization=rival_org,
            name="9z Team CS2",
            defaults={
                "game": cs2,
                "description": "Escuadra argentina de Counter-Strike 2.",
                "status": Team.Status.ACTIVE,
            },
        )
        rival_furious_lol, _ = Team.objects.get_or_create(
            organization=rival_org,
            name="Furious Gaming LoL",
            defaults={
                "game": lol,
                "description": "Equipo de League of Legends de la LLA.",
                "status": Team.Status.ACTIVE,
            },
        )
        rival_sentinels_val, _ = Team.objects.get_or_create(
            organization=rival_org,
            name="Sentinels Academy Valorant",
            defaults={
                "game": val,
                "description": "Academia de Sentinels en Valorant.",
                "status": Team.Status.ACTIVE,
            },
        )
        rival_mibr_cs2, _ = Team.objects.get_or_create(
            organization=rival_org,
            name="MIBR Academy CS2",
            defaults={
                "game": cs2,
                "description": "Academia de MIBR en Counter-Strike 2.",
                "status": Team.Status.ACTIVE,
            },
        )

        # Partidos Finalizados
        m1, _ = Match.objects.get_or_create(
            home_team=team_nxs_val,
            away_team=team_kru_val,
            scheduled_at=now - timedelta(days=4),
            defaults={
                "game": val,
                "kind": Match.Kind.TOURNAMENT,
                "status": Match.Status.FINISHED,
                "tournament_name": "VCT Americas Challengers 2026",
                "best_of": 3,
                "home_score": 2,
                "away_score": 1,
                "notes": "Gran desempeño de ViperX en Haven y remontada en Lotus.",
            },
        )
        # Mapas de m1
        MatchMap.objects.get_or_create(
            match=m1, order=1,
            defaults={"map_name": "Haven", "home_score": 13, "away_score": 9, "outcome": MatchMap.Outcome.HOME}
        )
        MatchMap.objects.get_or_create(
            match=m1, order=2,
            defaults={"map_name": "Ascent", "home_score": 8, "away_score": 13, "outcome": MatchMap.Outcome.AWAY}
        )
        MatchMap.objects.get_or_create(
            match=m1, order=3,
            defaults={"map_name": "Lotus", "home_score": 13, "away_score": 11, "outcome": MatchMap.Outcome.HOME}
        )

        m2, _ = Match.objects.get_or_create(
            home_team=team_nxs_lol,
            away_team=team_lev_lol,
            scheduled_at=now - timedelta(days=2),
            defaults={
                "game": lol,
                "kind": Match.Kind.OFFICIAL,
                "status": Match.Status.FINISHED,
                "tournament_name": "Liga Regional Sur 2026",
                "best_of": 3,
                "home_score": 2,
                "away_score": 0,
                "notes": "Control total de dragones y Barón en ambos mapas.",
            },
        )

        m3, _ = Match.objects.get_or_create(
            home_team=team_nxs_cs2,
            away_team=rival_9z_cs2,
            scheduled_at=now - timedelta(days=1),
            defaults={
                "game": cs2,
                "kind": Match.Kind.SCRIM,
                "status": Match.Status.FINISHED,
                "tournament_name": "Práctica Competitiva",
                "best_of": 3,
                "home_score": 1,
                "away_score": 2,
                "notes": "Buen test de ejecuciones en Inferno, ajustar rotaciones en Mirage.",
            },
        )

        # Partidos Programados (Futuros)
        Match.objects.get_or_create(
            home_team=team_nxs_val,
            away_team=rival_sentinels_val,
            scheduled_at=now + timedelta(days=2, hours=3),
            defaults={
                "game": val,
                "kind": Match.Kind.TOURNAMENT,
                "status": Match.Status.SCHEDULED,
                "tournament_name": "VCT Americas Challengers 2026 - Cuartos",
                "best_of": 3,
            },
        )
        Match.objects.get_or_create(
            home_team=team_nxs_lol,
            away_team=rival_furious_lol,
            scheduled_at=now + timedelta(days=4, hours=1),
            defaults={
                "game": lol,
                "kind": Match.Kind.OFFICIAL,
                "status": Match.Status.SCHEDULED,
                "tournament_name": "Liga Regional Sur - Semana 4",
                "best_of": 1,
            },
        )
        Match.objects.get_or_create(
            home_team=team_nxs_cs2,
            away_team=rival_mibr_cs2,
            scheduled_at=now + timedelta(days=6, hours=4),
            defaults={
                "game": cs2,
                "kind": Match.Kind.SCRIM,
                "status": Match.Status.SCHEDULED,
                "tournament_name": "Scrim Internacional",
                "best_of": 3,
            },
        )
        self.stdout.write(self.style.SUCCESS("  [+] Partidos finalizados y próximos registrados con marcadores y mapas"))

        # 10. Sesiones de Entrenamiento
        ts1, _ = TrainingSession.objects.get_or_create(
            team=team_nxs_val,
            title="Tácticas de retake y setups de sitios",
            scheduled_at=now - timedelta(days=1, hours=5),
            defaults={
                "duration_minutes": 120,
                "location": "Discord / Servidor Custom",
                "objectives": "Pulir comunicaciones bajo presión y cobertura en Bind y Haven.",
                "plan": "1. Calentamiento (20m)\n2. Retakes sitio A (40m)\n3. Retakes sitio B (40m)\n4. Retroalimentación (20m)",
                "status": TrainingSession.Status.COMPLETED,
            },
        )
        # Asistencias ts1
        for p in Player.objects.filter(team_assignments__team=team_nxs_val):
            TrainingAttendance.objects.get_or_create(
                session=ts1,
                player=p,
                defaults={"status": TrainingAttendance.Attendance.PRESENT},
            )

        ts2, _ = TrainingSession.objects.get_or_create(
            team=team_nxs_lol,
            title="Estrategia de fase de líneas y control de visión",
            scheduled_at=now + timedelta(days=1, hours=2),
            defaults={
                "duration_minutes": 90,
                "location": "Gaming House Sala 1",
                "objectives": "Coordinar sincronización de oleadas y rotaciones al Heraldo.",
                "plan": "Simulación de primeros 15 minutos en scrim interna.",
                "status": TrainingSession.Status.PLANNED,
            },
        )
        self.stdout.write(self.style.SUCCESS("  [+] Sesiones de entrenamiento y control de asistencia creados"))

        self.stdout.write(self.style.SUCCESS("\n¡Base de datos poblada exitosamente con todos los módulos!"))
        self.stdout.write(self.style.SUCCESS("Credenciales de superusuario: admin / Nexus2026"))
