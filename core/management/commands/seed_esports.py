"""Comando para ampliar la base de datos con juegos, equipos y jugadores.

Añade de forma idempotente los juegos que faltan, dos equipos conocidos por
juego (con sus jugadores actuales) y descarga/ genera el logo de cada equipo.

Ejecución:
    python manage.py seed_esports
    python manage.py seed_esports --no-logos
"""

import io
import urllib.request

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from organizations.models import Game, GameRole, Organization, Team
from players.models import Player, PlayerTeamAssignment

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) NexusSeed/1.0"

# ---------------------------------------------------------------------------
# Organizaciones (con dominios candidatos para obtener su logo)
# ---------------------------------------------------------------------------
ORGS = [
    {
        "slug": "team-falcons",
        "name": "Team Falcons",
        "abbreviation": "FLC",
        "country": "Arabia Saudita",
        "description": "Organización saudí con equipos en múltiples disciplinas.",
        "founded_date": "2020-01-01",
        "domains": ["falcons.sa"],
    },
    {
        "slug": "cloud9",
        "name": "Cloud9",
        "abbreviation": "C9",
        "country": "Estados Unidos",
        "description": "Una de las organizaciones más reconocidas de Norteamérica.",
        "founded_date": "2012-12-01",
        "domains": ["cloud9.gg"],
    },
    {
        "slug": "team-liquid",
        "name": "Team Liquid",
        "abbreviation": "TL",
        "country": "Países Bajos",
        "description": "Organización neerlandesa presente en decenas de juegos.",
        "founded_date": "2000-01-01",
        "domains": ["teamliquid.com"],
    },
    {
        "slug": "optic-gaming",
        "name": "OpTic Gaming",
        "abbreviation": "OPT",
        "country": "Estados Unidos",
        "description": "Marca histórica de los esports norteamericanos.",
        "founded_date": "2006-01-01",
        "domains": ["opticgaming.com"],
    },
    {
        "slug": "gen-g",
        "name": "Gen.G",
        "abbreviation": "GEN",
        "country": "Corea del Sur",
        "description": "Organización coreana con presencia global en esports.",
        "founded_date": "2017-08-01",
        "domains": ["gengesports.com"],
    },
    {
        "slug": "onic-esports",
        "name": "ONIC Esports",
        "abbreviation": "ONIC",
        "country": "Indonesia",
        "description": "Potencia del sudeste asiático en juegos móviles.",
        "founded_date": "2018-01-01",
        "domains": ["onic-esports.com"],
    },
    {
        "slug": "blacklist-international",
        "name": "Blacklist International",
        "abbreviation": "BLCK",
        "country": "Filipinas",
        "description": "Organización filipina referente en Mobile Legends.",
        "founded_date": "2017-01-01",
        "domains": ["blacklistinternational.com"],
    },
    {
        "slug": "wolves-esports",
        "name": "Wolves Esports",
        "abbreviation": "WOLV",
        "country": "China",
        "description": "Organización china con equipos en la KPL.",
        "founded_date": "2017-01-01",
        "domains": ["wolves-esports.com"],
    },
    {
        "slug": "estar-gaming",
        "name": "eStar Gaming",
        "abbreviation": "ESTAR",
        "country": "China",
        "description": "Club chino con presencia en ligas de juegos móviles.",
        "founded_date": "2014-01-01",
        "domains": ["estar.gg"],
    },
    {
        "slug": "crazy-raccoon",
        "name": "Crazy Raccoon",
        "abbreviation": "CR",
        "country": "Japón",
        "description": "Organización japonesa destacada en FPS y OWCS.",
        "founded_date": "2017-01-01",
        "domains": ["crazyraccoon.jp"],
    },
    {
        "slug": "tsm",
        "name": "TSM",
        "abbreviation": "TSM",
        "country": "Estados Unidos",
        "description": "Organización norteamericana histórica en FPS y Apex.",
        "founded_date": "2009-01-01",
        "domains": ["tsm.gg"],
    },
    {
        "slug": "darkzero",
        "name": "DarkZero Esports",
        "abbreviation": "DZ",
        "country": "Estados Unidos",
        "description": "Organización reconocida en Apex Legends y Rainbow Six.",
        "founded_date": "2018-01-01",
        "domains": ["darkzero.gg"],
    },
    {
        "slug": "m80",
        "name": "M80",
        "abbreviation": "M80",
        "country": "Estados Unidos",
        "description": "Organización norteamericana con equipos en FPS.",
        "founded_date": "2022-01-01",
        "domains": ["m80.gg"],
    },
]

# ---------------------------------------------------------------------------
# Juegos que faltan (con sus roles y sus dos equipos + jugadores)
# ---------------------------------------------------------------------------
GAMES = [
    {
        "slug": "overwatch-2",
        "name": "Overwatch 2",
        "short_name": "OW2",
        "default_team_size": 5,
        "roles": [
            ("Tanque", "TANK", "Inicia el combate y absorbe el daño enemigo."),
            ("DPS", "DPS", "Principal fuente de daño y eliminaciones."),
            ("Soporte", "SUPP", "Curación y utilidades para el equipo."),
        ],
        "teams": [
            {
                "org": "team-falcons",
                "name": "Team Falcons OW2",
                "slug": "falcons-ow2",
                "description": "Roster coreano de Overwatch 2 de Team Falcons.",
                "players": [
                    ("Proper", "Kim", "Dong-hyun", "Corea del Sur", "DPS", True, 1),
                    ("Fielder", "Kwon", "Joon-hyeong", "Corea del Sur", "Soporte", False, 3),
                    ("ChiYo", "Son", "Chi-yong", "Corea del Sur", "Soporte", False, 4),
                    ("MER1T", "Kim", "Min-jun", "Corea del Sur", "DPS", False, 5),
                    ("SOMEONE", "Kang", "Min-su", "Corea del Sur", "Tanque", False, 6),
                ],
            },
            {
                "org": "crazy-raccoon",
                "name": "Crazy Raccoon",
                "slug": "crazy-raccoon-ow2",
                "description": "Escuadra japonesa de referencia en OWCS.",
                "players": [
                    ("Heesang", "Kim", "Hee-sang", "Corea del Sur", "DPS", True, 7),
                    ("LIP", "Lee", "Jae-won", "Corea del Sur", "DPS", False, 8),
                    ("Fleta", "Kim", "Byung-sun", "Corea del Sur", "DPS", False, 9),
                    ("Shu", "Kim", "Seung-hyun", "Corea del Sur", "Soporte", False, 10),
                    ("Junbin", "Ko", "Jun-bin", "Corea del Sur", "Tanque", False, 11),
                ],
            },
        ],
    },
    {
        "slug": "rainbow-six-siege",
        "name": "Rainbow Six Siege",
        "short_name": "R6",
        "default_team_size": 5,
        "roles": [
            ("Entrada", "ENTRY", "Primera línea de ataque."),
            ("Soporte", "SUPP", "Utilidades y cobertura para el equipo."),
            ("Ancla", "ANCHOR", "Defensa fija de objetivos."),
            ("Acechador", "LURK", "Control silencioso de flancos."),
            ("In-Game Leader", "IGL", "Estratega y capitán del equipo."),
        ],
        "teams": [
            {
                "org": "g2-esports",
                "name": "G2 Esports R6",
                "slug": "g2-r6",
                "description": "Escuadra europea de Rainbow Six Siege.",
                "players": [
                    ("CTZN", "Ben", "McMillan", "Reino Unido", "In-Game Leader", True, 1),
                    ("Virtue", "Jake", "Grannan", "Reino Unido", "Entrada", False, 2),
                    ("Kanto", "Ilias", "El Kanto", "Marruecos", "Soporte", False, 3),
                    ("Alem4o", "Gabriel", "Nunes", "Brasil", "Ancla", False, 4),
                    ("Dropped", "Arthur", "Lima", "Brasil", "Acechador", False, 5),
                ],
            },
            {
                "org": "team-liquid",
                "name": "Team Liquid R6",
                "slug": "liquid-r6",
                "description": "Roster brasileño de Team Liquid en Rainbow Six.",
                "players": [
                    ("Paluh", "Luiz", "Paluh", "Brasil", "In-Game Leader", True, 1),
                    ("nesk", "Thiago", "Nesk", "Brasil", "Entrada", False, 2),
                    ("nade", "Gabriel", "Nade", "Brasil", "Soporte", False, 3),
                    ("SexyCake", "João", "Cake", "Brasil", "Ancla", False, 4),
                    ("AsK", "Felipe", "Ask", "Brasil", "Acechador", False, 5),
                ],
            },
        ],
    },
    {
        "slug": "apex-legends",
        "name": "Apex Legends",
        "short_name": "APEX",
        "default_team_size": 3,
        "roles": [
            ("In-Game Leader", "IGL", "Toma las decisiones tácticas del trío."),
            ("Fragger", "FRAG", "Busca y cierra eliminaciones."),
            ("Soporte", "SUPP", "Apoyo, curación y utilidades."),
        ],
        "teams": [
            {
                "org": "tsm",
                "name": "TSM",
                "slug": "tsm-apex",
                "description": "Trío histórico de Apex Legends con títulos mundiales.",
                "players": [
                    ("Reps", "Jordan", "Wolfe", "Estados Unidos", "In-Game Leader", True, 1),
                    ("Verhulst", "Evan", "Verhulst", "Estados Unidos", "Fragger", False, 2),
                    ("Zap", "Cody", "Zap", "Estados Unidos", "Soporte", False, 3),
                ],
            },
            {
                "org": "darkzero",
                "name": "DarkZero",
                "slug": "darkzero-apex",
                "description": "Uno de los tríos más dominantes de la escena.",
                "players": [
                    ("Zer0", "Rhys", "Perry", "Australia", "In-Game Leader", True, 1),
                    ("Genburten", "Noyan", "Ozkose", "Australia", "Fragger", False, 2),
                    ("Sharky", "Matthew", "Shark", "Australia", "Soporte", False, 3),
                ],
            },
        ],
    },
    {
        "slug": "call-of-duty-league",
        "name": "Call of Duty League",
        "short_name": "CDL",
        "default_team_size": 4,
        "roles": [
            ("AR", "AR", "Rifle de asalto de largo alcance."),
            ("SMG", "SMG", "Subfusil de agresión cercana."),
            ("Flexible", "FLEX", "Juega cualquier arma según el mapa."),
            ("Suplente", "SUB", "Rotación y reemplazo del roster."),
        ],
        "teams": [
            {
                "org": "faze-clan",
                "name": "Atlanta FaZe",
                "slug": "atlanta-faze-cod",
                "description": "Una de las escuadras más exitosas de la CDL.",
                "players": [
                    ("Simp", "Chris", "Lehr", "Estados Unidos", "SMG", True, 1),
                    ("aBeZy", "Tyler", "Pharris", "Estados Unidos", "SMG", False, 2),
                    ("Cellium", "McArthur", "Jovel", "Estados Unidos", "AR", False, 3),
                    ("Drazah", "Jordan", "Kent", "Estados Unidos", "AR", False, 4),
                ],
            },
            {
                "org": "optic-gaming",
                "name": "OpTic Texas",
                "slug": "optic-texas-cod",
                "description": "Marca histórica de Call of Duty.",
                "players": [
                    ("Shotzzy", "Anthony", "Cuevas-Castro", "Estados Unidos", "SMG", True, 1),
                    ("Pred", "Amer", "Zulbeari", "Australia", "SMG", False, 2),
                    ("Dashy", "Brandon", "Otell", "Estados Unidos", "AR", False, 3),
                    ("Kenny", "Kenny", "Williams", "Estados Unidos", "AR", False, 4),
                ],
            },
        ],
    },
    {
        "slug": "pubg",
        "name": "PUBG: Battlegrounds",
        "short_name": "PUBG",
        "default_team_size": 4,
        "roles": [
            ("In-Game Leader", "IGL", "Coordina rotaciones y decisiones."),
            ("Fragger", "FRAG", "Principal fuente de eliminaciones."),
            ("Soporte", "SUPP", "Cobertura y utilidades."),
            ("Explorador", "SCOUT", "Información y control de mapa."),
        ],
        "teams": [
            {
                "org": "natus-vincere",
                "name": "Natus Vincere PUBG",
                "slug": "navi-pubg",
                "description": "Escuadra europea de PUBG de NAVI.",
                "players": [
                    ("ceh9", "Arseniy", "Ivanyuk", "Ucrania", "In-Game Leader", True, 1),
                    ("A1F4", "Aleksandr", "Kalmakov", "Rusia", "Fragger", False, 2),
                    ("WILL", "Vladislav", "Skorobogatov", "Rusia", "Soporte", False, 3),
                    ("zvz", "Zaur", "Bazgaraev", "Rusia", "Explorador", False, 4),
                ],
            },
            {
                "org": "gen-g",
                "name": "Gen.G PUBG",
                "slug": "geng-pubg",
                "description": "Equipo coreano dominante en PUBG.",
                "players": [
                    ("Inonix", "Na", "Jin-wook", "Corea del Sur", "Fragger", True, 1),
                    ("Loki", "Yoon", "Sung-hyun", "Corea del Sur", "In-Game Leader", False, 2),
                    ("Taemin", "Lee", "Tae-min", "Corea del Sur", "Soporte", False, 3),
                    ("Heine", "Kim", "Heine", "Corea del Sur", "Explorador", False, 4),
                ],
            },
        ],
    },
    {
        "slug": "mobile-legends-bang-bang",
        "name": "Mobile Legends: Bang Bang",
        "short_name": "MLBB",
        "default_team_size": 5,
        "roles": [
            ("EXP Lane", "EXP", "Línea de experiencia, héroe resistente."),
            ("Jungla", "JUNGLE", "Control de objetivos y gankeos."),
            ("Medio", "MID", "Línea central de daño mágico."),
            ("Oro", "GOLD", "Tirador principal del equipo."),
            ("Roam", "ROAM", "Rotaciones y visión."),
        ],
        "teams": [
            {
                "org": "onic-esports",
                "name": "ONIC Esports",
                "slug": "onic-mlbb",
                "description": "Roster campeón de la MPL Indonesia.",
                "players": [
                    ("Kiboy", "Nicky", "Fernando", "Indonesia", "Roam", True, 1),
                    ("Sanz", "Gilang", "Sanz", "Indonesia", "Jungla", False, 2),
                    ("Butsss", "Muhammad", "Butsss", "Indonesia", "Oro", False, 3),
                    ("Kairi", "Kairi", "Kairi", "Indonesia", "EXP Lane", False, 4),
                    ("CW", "Calvin", "Winata", "Indonesia", "Medio", False, 5),
                ],
            },
            {
                "org": "blacklist-international",
                "name": "Blacklist International",
                "slug": "blacklist-mlbb",
                "description": "Leyenda filipina de Mobile Legends.",
                "players": [
                    ("Wise", "Danerie", "Del Rosario", "Filipinas", "Jungla", True, 1),
                    ("OhMyV33NUS", "Johnmar", "Villaluna", "Filipinas", "Roam", False, 2),
                    ("Hadji", "Salic", "Imam", "Filipinas", "Medio", False, 3),
                    ("Edward", "Edward", "Fernandez", "Filipinas", "EXP Lane", False, 4),
                    ("Super Marco", "Marco", "Requitano", "Filipinas", "Oro", False, 5),
                ],
            },
        ],
    },
    {
        "slug": "honor-of-kings",
        "name": "Honor of Kings",
        "short_name": "HOK",
        "default_team_size": 5,
        "roles": [
            ("Top", "TOP", "Línea superior, héroe de sola vía."),
            ("Jungla", "JUNGLE", "Control de objetivos neutrales."),
            ("Medio", "MID", "Línea central de daño mágico."),
            ("ADC", "ADC", "Tirador de daño sostenido."),
            ("Soporte", "SUPP", "Protección y control."),
        ],
        "teams": [
            {
                "org": "wolves-esports",
                "name": "Wolves Esports",
                "slug": "wolves-hok",
                "description": "Escuadra china campeona de la KPL.",
                "players": [
                    ("Fly", "Peng", "Yunfei", "China", "Top", True, 1),
                    ("Cat", "Cheng", "Guo", "China", "Medio", False, 2),
                    ("Yan", "Yan", "Yan", "China", "Jungla", False, 3),
                    ("YiNu", "Li", "Yinuo", "China", "ADC", False, 4),
                    ("Sword", "Sword", "Sword", "China", "Soporte", False, 5),
                ],
            },
            {
                "org": "estar-gaming",
                "name": "eStar Pro",
                "slug": "estar-hok",
                "description": "Club histórico de la liga china de Honor of Kings.",
                "players": [
                    ("Clear", "Xu", "Bicheng", "China", "Top", True, 1),
                    ("Skey", "Skey", "Skey", "China", "Jungla", False, 2),
                    ("Qingrong", "Qingrong", "Qingrong", "China", "Medio", False, 3),
                    ("ZiMo", "ZiMo", "ZiMo", "China", "ADC", False, 4),
                    ("Tutu", "Tutu", "Tutu", "China", "Soporte", False, 5),
                ],
            },
        ],
    },
    {
        "slug": "starcraft-2",
        "name": "StarCraft II",
        "short_name": "SC2",
        "default_team_size": 1,
        "roles": [
            ("Terran", "TERRAN", "Especialista en la raza Terran."),
            ("Zerg", "ZERG", "Especialista en la raza Zerg."),
            ("Protoss", "PROTOSS", "Especialista en la raza Protoss."),
        ],
        "teams": [
            {
                "org": "t1",
                "name": "T1 StarCraft",
                "slug": "t1-sc2",
                "description": "Equipo coreano con grandes figuras del RTS.",
                "players": [
                    ("Maru", "Cho", "Seong-ju", "Corea del Sur", "Terran", True, 1),
                    ("Cure", "Kim", "Doh-wook", "Corea del Sur", "Terran", False, 2),
                    ("Dream", "Jo", "Joong-hyuk", "Corea del Sur", "Terran", False, 3),
                    ("Solar", "Kang", "Min-soo", "Corea del Sur", "Zerg", False, 4),
                ],
            },
            {
                "org": "team-liquid",
                "name": "Team Liquid StarCraft",
                "slug": "liquid-sc2",
                "description": "Potencia internacional en StarCraft II.",
                "players": [
                    ("Clem", "Clément", "Desplanches", "Francia", "Terran", True, 1),
                    ("Serral", "Joona", "Sotala", "Finlandia", "Zerg", False, 2),
                    ("HerO", "Kim", "Joon-ho", "Corea del Sur", "Protoss", False, 3),
                    ("ShoWTimE", "Tobias", "Sieber", "Alemania", "Protoss", False, 4),
                ],
            },
        ],
    },
    {
        "slug": "tekken-8",
        "name": "Tekken 8",
        "short_name": "T8",
        "default_team_size": 1,
        "roles": [
            ("Mishima", "MISH", "Especialista en el estilo Mishima."),
            ("Striker", "STRIKE", "Combatiente ofensivo de presión."),
            ("Grappler", "GRAPP", "Especialista en agarres y castigos."),
            ("Especialista", "SPEC", "Dominio de un personaje concreto."),
        ],
        "teams": [
            {
                "org": "team-liquid",
                "name": "Team Liquid Tekken",
                "slug": "liquid-t8",
                "description": "Escuadra internacional de Tekken.",
                "players": [
                    ("Arslan Ash", "Arslan", "Siddique", "Pakistán", "Mishima", True, 1),
                    ("Atif", "Atif", "Butt", "Pakistán", "Striker", False, 2),
                    ("ULSAN", "Lim", "Ul-san", "Corea del Sur", "Mishima", False, 3),
                    ("Knee", "Bae", "Jae-min", "Corea del Sur", "Especialista", False, 4),
                ],
            },
            {
                "org": "team-falcons",
                "name": "Team Falcons Tekken",
                "slug": "falcons-t8",
                "description": "Roster japonés y coreano de Tekken 8.",
                "players": [
                    ("Double", "Kim", "Myeong-hwan", "Corea del Sur", "Mishima", True, 1),
                    ("Nobi", "Daichi", "Nakayama", "Japón", "Especialista", False, 2),
                    ("Chikurin", "Ryota", "Take", "Japón", "Striker", False, 3),
                    ("Yamasa", "Yuji", "Yamasa", "Japón", "Grappler", False, 4),
                ],
            },
        ],
    },
    {
        "slug": "street-fighter-6",
        "name": "Street Fighter 6",
        "short_name": "SF6",
        "default_team_size": 1,
        "roles": [
            ("Shoto", "SHOTO", "Estilo equilibrado de fuego y presión."),
            ("Grappler", "GRAPP", "Especialista en agarres."),
            ("Zoner", "ZONER", "Control de distancia y proyectiles."),
            ("Rushdown", "RUSH", "Presión ofensiva constante."),
        ],
        "teams": [
            {
                "org": "m80",
                "name": "M80 Street Fighter",
                "slug": "m80-sf6",
                "description": "Escuadra estadounidense de Street Fighter 6.",
                "players": [
                    ("Punk", "Victor", "Woodley", "Estados Unidos", "Rushdown", True, 1),
                    ("NuckleDu", "Du", "Dang", "Estados Unidos", "Zoner", False, 2),
                    ("Caba", "Michael", "Caba", "República Dominicana", "Shoto", False, 3),
                    ("MenaRD", "Saul", "Mena", "República Dominicana", "Grappler", False, 4),
                ],
            },
            {
                "org": "fnatic",
                "name": "Fnatic Street Fighter",
                "slug": "fnatic-sf6",
                "description": "Equipo internacional de Street Fighter de Fnatic.",
                "players": [
                    ("Problem X", "Benjamin", "Simon", "Reino Unido", "Shoto", True, 1),
                    ("Kawano", "Masaki", "Kawano", "Japón", "Shoto", False, 2),
                    ("Fujimura", "Yusuke", "Fujimura", "Japón", "Rushdown", False, 3),
                    ("EndingWalker", "Christopher", "Walker", "Reino Unido", "Grappler", False, 4),
                ],
            },
        ],
    },
]

PLACEHOLDER_COLORS = [
    "#e63946", "#457b9d", "#2a9d8f", "#e9c46a", "#f4a261",
    "#8338ec", "#3a86ff", "#fb5607", "#06d6a0", "#118ab2",
]


class Command(BaseCommand):
    help = "Añade los juegos, equipos, jugadores y logos que faltan (idempotente)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-logos",
            action="store_true",
            help="No descarga ni genera logos para los equipos.",
        )

    # ------------------------------------------------------------------
    def handle(self, *args, **options):
        self.with_logos = not options["no_logos"]

        self.stdout.write(self.style.NOTICE("Iniciando ampliación de datos de esports..."))

        orgs = self._create_orgs()
        self._create_games(orgs)

        self.stdout.write(self.style.SUCCESS("Proceso finalizado."))

    # ------------------------------------------------------------------
    def _create_orgs(self):
        orgs = {}
        for data in ORGS:
            website = f"https://{data['domains'][0]}" if data.get("domains") else ""
            org, created = Organization.objects.get_or_create(
                slug=data["slug"],
                defaults={
                    "name": data["name"],
                    "abbreviation": data["abbreviation"],
                    "country": data["country"],
                    "website": website,
                    "description": data["description"],
                    "founded_date": data["founded_date"],
                    "is_active": True,
                },
            )
            if not created and not org.website and website:
                org.website = website
                org.save(update_fields=["website"])
            orgs[data["slug"]] = org
        # Organizaciones ya existentes que se reutilizan
        self.stdout.write(self.style.SUCCESS(f"  [+] Organizaciones listas: {Organization.objects.count()}"))
        return orgs

    # ------------------------------------------------------------------
    def _create_games(self, orgs):
        for game_data in GAMES:
            game, created = Game.objects.get_or_create(
                slug=game_data["slug"],
                defaults={
                    "name": game_data["name"],
                    "short_name": game_data["short_name"],
                    "default_team_size": game_data["default_team_size"],
                    "is_active": True,
                },
            )
            if created:
                self.stdout.write(f"  [+] Juego creado: {game.name}")

            roles = {}
            for name, abbr, desc in game_data["roles"]:
                role, _ = GameRole.objects.get_or_create(
                    game=game,
                    name=name,
                    defaults={"abbreviation": abbr, "description": desc},
                )
                roles[name] = role

            for team_data in game_data["teams"]:
                org = self._resolve_org(orgs, team_data["org"])
                team, t_created = Team.objects.get_or_create(
                    organization=org,
                    game=game,
                    name=team_data["name"],
                    defaults={
                        "slug": team_data["slug"],
                        "description": team_data["description"],
                        "status": Team.Status.ACTIVE,
                    },
                )
                if t_created:
                    self.stdout.write(f"      -> Equipo: {team.name} ({org.name})")
                    if self.with_logos:
                        self._attach_logo(team, org, team_data.get("logo_domains"))

                self._create_players(team, team_data["players"], roles)

    # ------------------------------------------------------------------
    def _resolve_org(self, orgs, slug):
        if slug in orgs:
            return orgs[slug]
        return Organization.objects.get(slug=slug)

    # ------------------------------------------------------------------
    def _create_players(self, team, players, roles):
        for nick, first, last, country, role_name, captain, jersey in players:
            player, _ = Player.objects.get_or_create(
                nickname=nick,
                defaults={
                    "first_name": first,
                    "last_name": last,
                    "country": country,
                    "email": f"{slugify(nick)}@esports.gg",
                },
            )
            already = PlayerTeamAssignment.objects.filter(
                player=player, team=team, left_at__isnull=True
            ).exists()
            if not already:
                PlayerTeamAssignment.objects.create(
                    player=player,
                    team=team,
                    competitive_role=roles[role_name],
                    jersey_number=jersey,
                    joined_at="2025-01-15",
                    status=PlayerTeamAssignment.Status.ACTIVE,
                    is_captain=captain,
                )

    # ------------------------------------------------------------------
    def _attach_logo(self, team, org, extra_domains=None):
        # 1. Reutiliza el logo de otro equipo de la misma organización.
        sibling = (
            Team.objects.filter(organization=org)
            .exclude(logo="")
            .exclude(logo__isnull=True)
            .exclude(pk=team.pk)
            .first()
        )
        if sibling and sibling.logo:
            try:
                with sibling.logo.open("rb") as fh:
                    team.logo.save(f"{slugify(team.name)}.png", ContentFile(fh.read()), save=True)
                return
            except Exception:
                pass

        # 2. Descarga desde los dominios candidatos.
        domains = list(extra_domains or []) + list(org_website_domains(org))
        blob = fetch_logo(domains)

        # 3. Último recurso: placeholder con la abreviatura.
        if blob is None:
            blob = make_placeholder(org.abbreviation or org.name)

        filename = f"{slugify(team.name)}.png"
        team.logo.save(filename, ContentFile(blob), save=True)


# ---------------------------------------------------------------------------
# Utilidades de logos
# ---------------------------------------------------------------------------
def org_website_domains(org):
    if not org.website:
        return []
    return [org.website.replace("https://", "").replace("http://", "").strip("/")]


def fetch_logo(domains):
    """Intenta descargar un logo desde los servicios de favicon conocidos."""
    seen = set()
    for domain in domains:
        domain = (domain or "").strip().lower()
        if not domain or domain in seen:
            continue
        seen.add(domain)
        candidates = [
            f"https://t3.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON"
            f"&fallback_opts=TYPE,SIZE,URL&url=https://{domain}&size=256",
            f"https://icons.duckduckgo.com/ip3/{domain}.ico",
        ]
        for url in candidates:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=20) as resp:
                    data = resp.read()
                if data and len(data) > 200:
                    return normalize_image(data)
            except Exception:
                continue
    return None


def normalize_image(data):
    """Re-codifica la imagen a PNG para homogeneizar formatos."""
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(data)).convert("RGBA")
        img.thumbnail((256, 256))
        out = io.BytesIO()
        img.save(out, format="PNG")
        return out.getvalue()
    except Exception:
        return None


def make_placeholder(text):
    """Genera un logo PNG con el texto/abreviatura de la organización."""
    from PIL import Image, ImageDraw, ImageFont

    size = 256
    color = PLACEHOLDER_COLORS[sum(ord(c) for c in text) % len(PLACEHOLDER_COLORS)]
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((8, 8, size - 8, size - 8), fill=color)

    label = (text or "?")[:4].upper()
    try:
        font = ImageFont.truetype("arialbd.ttf", 96 if len(label) <= 2 else 72)
    except Exception:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), label, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(
        ((size - w) / 2 - bbox[0], (size - h) / 2 - bbox[1]),
        label,
        fill="white",
        font=font,
    )
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()
