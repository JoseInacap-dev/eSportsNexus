"""Amplia la base con equipos de primer nivel de Valorant y League of Legends.

De forma idempotente crea las organizaciones que falten, lleva Valorant y
League of Legends a 16 equipos cada uno (plantilla de 5 jugadores + coach) y
añade cuerpo técnico (head coach, analista y manager) para los equipos nuevos.

Ejecución:
    python manage.py seed_val_lol
"""

from datetime import date

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from organizations.models import Game, Organization, Team
from players.models import Player, PlayerTeamAssignment
from staff.models import StaffMember, TeamStaffAssignment

VAL = "valorant"
LOL = "league-of-legends"

JOINED = date(2025, 1, 15)
STAFF_STARTED = date(2025, 1, 15)

# ---------------------------------------------------------------------------
# Organizaciones nuevas (slug, nombre, abreviatura, país, fundación, descripción)
# ---------------------------------------------------------------------------
ORGS = [
    ("team-heretics", "Team Heretics", "TH", "España", "2016-01-01", "Organización española de gran crecimiento con equipos en varios títulos."),
    ("drx", "DRX", "DRX", "Corea del Sur", "2019-01-01", "Organización surcoreana con escuadras de élite en Valorant y LoL."),
    ("edward-gaming", "EDward Gaming", "EDG", "China", "2013-09-01", "Organización china multiplataforma, dominante en Valorant."),
    ("funplus-phoenix", "FunPlus Phoenix", "FPX", "China", "2017-12-01", "Organización china campeona del mundo de League of Legends."),
    ("bilibili-gaming", "Bilibili Gaming", "BLG", "China", "2017-01-01", "Organización china con equipos de primer nivel."),
    ("nrg", "NRG", "NRG", "Estados Unidos", "2015-10-01", "Organización norteamericana presente en varios de los principales juegos."),
    ("leviatan", "Leviatán", "LEV", "Chile", "2021-01-01", "Organización latinoamericana de élite liderada desde Chile."),
    ("top-esports", "Top Esports", "TES", "China", "2017-12-01", "Organización china con plantilla de superestrellas."),
    ("weibo-gaming", "Weibo Gaming", "WBG", "China", "2013-01-01", "Organización china finalista del mundial de League of Legends."),
    ("mad-lions-koi", "MAD Lions KOI", "MAD", "España", "2017-01-01", "Organización europea con una de las mayores hinchadas de la LEC."),
    ("team-vitality", "Team Vitality", "VIT", "Francia", "2013-08-05", "El club francés más importante y campeón de la LEC."),
    ("sk-gaming", "SK Gaming", "SK", "Alemania", "1997-01-01", "Organización alemana pionera de los esports."),
    ("kt-rolster", "KT Rolster", "KT", "Corea del Sur", "1999-01-01", "Organización surcoreana histórica de la LCK."),
    ("hanwha-life-esports", "Hanwha Life Esports", "HLE", "Corea del Sur", "2018-01-01", "Organización coreana campeona de la LCK."),
    ("dplus-kia", "Dplus KIA", "DK", "Corea del Sur", "2012-01-01", "Organización coreana campeona del mundo de LoL."),
    ("cloud9", "Cloud9", "C9", "Estados Unidos", "2013-01-01", "Organización norteamericana multiplataforma."),
]

# ---------------------------------------------------------------------------
# Equipos y plantillas
# players: (nickname, nombre, apellidos, país, rol, capitán)
# coach:   (nickname, nombre, apellidos, país)
# staff:   (nombre, apellidos, rol, país)  -> se añade además el head coach
# ---------------------------------------------------------------------------
TEAMS = [
    # ------------------------------- Valorant ------------------------------
    {
        "game": VAL, "org": "team-heretics", "name": "Team Heretics Valorant",
        "description": "Escuadra española campeona de EMEA con un juego explosivo.",
        "founded_date": "2016-01-01",
        "players": [
            ("Boo", "Ricardas", "Lukasevicius", "Lituania", "CTRL", True),
            ("MiniBoo", "Dominykas", "Lukasevicius", "Lituania", "SENT", False),
            ("Wo0t", "Mert", "Alkan", "Turquía", "DUEL", False),
            ("RieNs", "Maksym", "Rieznik", "Ucrania", "INIT", False),
            ("paTiTek", "Patryk", "Fabrowski", "Polonia", "FLEX", False),
        ],
        "coach": ("neptuNo", "Nicolás", "González", "España"),
        "staff": [
            ("Alejandro", "Ruiz", "analyst", "España"),
            ("Marta", "Pérez", "manager", "España"),
        ],
    },
    {
        "game": VAL, "org": "team-liquid", "name": "Team Liquid Valorant",
        "description": "Marca histórica de los esports con presencia global en Valorant.",
        "founded_date": "2000-08-01",
        "players": [
            ("nAts", "Ayaz", "Akhmetzyanov", "Rusia", "INIT", True),
            ("Jamppi", "Elias", "Olkkonen", "Finlandia", "DUEL", False),
            ("kamo", "Timur", "Kadyrov", "Rusia", "CTRL", False),
            ("Mistic", "James", "Orfila", "Reino Unido", "SENT", False),
            ("Keiko", "Keiko", "Martínez", "Estados Unidos", "FLEX", False),
        ],
        "coach": ("Sliggy", "Connor", "Blomfield", "Reino Unido"),
        "staff": [
            ("Lauri", "Koski", "analyst", "Finlandia"),
            ("Rik", "van Dijk", "manager", "Países Bajos"),
        ],
    },
    {
        "game": VAL, "org": "drx", "name": "DRX Valorant",
        "description": "Escuadra coreana referente del Pacífico en el VCT.",
        "founded_date": "2019-01-01",
        "players": [
            ("stax", "Kim", "Gu-taek", "Corea del Sur", "INIT", True),
            ("Rb", "Goo", "Sang-min", "Corea del Sur", "DUEL", False),
            ("Zest", "Kim", "Yeon-tae", "Corea del Sur", "DUEL", False),
            ("BuZz", "Yoo", "Byung-chul", "Corea del Sur", "CTRL", False),
            ("MaKo", "Kim", "Myeong-gwan", "Corea del Sur", "SENT", False),
        ],
        "coach": ("Termi", "Kim", "Seong-jun", "Corea del Sur"),
        "staff": [
            ("Park", "Ji-hoon", "analyst", "Corea del Sur"),
            ("Lee", "Sang-hoon", "manager", "Corea del Sur"),
        ],
    },
    {
        "game": VAL, "org": "gen-g", "name": "Gen.G Valorant",
        "description": "Organización global con una plantilla de élite en el VCT Pacífico.",
        "founded_date": "2017-07-01",
        "players": [
            ("t3xture", "Kim", "Na-ra", "Corea del Sur", "DUEL", True),
            ("Meteor", "Ahn", "Byeong-hyeon", "Corea del Sur", "DUEL", False),
            ("Lakia", "Kim", "Jong-min", "Corea del Sur", "INIT", False),
            ("Karon", "Lee", "Won-tae", "Corea del Sur", "CTRL", False),
            ("Munchkin", "Byeon", "Sang-beom", "Corea del Sur", "SENT", False),
        ],
        "coach": ("hsk", "Hwang", "Sung-min", "Corea del Sur"),
        "staff": [
            ("Oh", "Jun-hyuk", "analyst", "Corea del Sur"),
            ("Choi", "Min-seo", "manager", "Corea del Sur"),
        ],
    },
    {
        "game": VAL, "org": "t1", "name": "T1 Valorant",
        "description": "Equipo legendario con presencia competitiva en múltiples títulos.",
        "founded_date": "2019-12-01",
        "players": [
            ("xccurate", "Kevin", "Susanto", "Indonesia", "CTRL", True),
            ("Sylvan", "Ko", "Young-sub", "Corea del Sur", "INIT", False),
            ("izu", "Park", "Min-jae", "Corea del Sur", "DUEL", False),
            ("iNTRO", "Choi", "Woo-jin", "Corea del Sur", "SENT", False),
            ("Carpe", "Lee", "Jae-hyeok", "Corea del Sur", "FLEX", False),
        ],
        "coach": ("indigo", "Cha", "Ji-hoon", "Corea del Sur"),
        "staff": [
            ("Yoon", "Tae-sik", "analyst", "Corea del Sur"),
            ("Jin", "Ho-young", "manager", "Corea del Sur"),
        ],
    },
    {
        "game": VAL, "org": "edward-gaming", "name": "EDward Gaming Valorant",
        "description": "Organización china dominante de la VCT China.",
        "founded_date": "2013-09-01",
        "players": [
            ("CHICHOO", "Wang", "Senxu", "China", "INIT", True),
            ("Smoggy", "Zhang", "Bocheng", "China", "CTRL", False),
            ("nobody", "Cheng", "Wan", "China", "SENT", False),
            ("Haodong", "Zhang", "Haodong", "China", "DUEL", False),
            ("KangKang", "Liu", "Kang", "China", "FLEX", False),
        ],
        "coach": ("AfteR", "Lai", "Xue-bin", "China"),
        "staff": [
            ("Zeng", "Wei", "analyst", "China"),
            ("Chen", "Jie", "manager", "China"),
        ],
    },
    {
        "game": VAL, "org": "funplus-phoenix", "name": "FunPlus Phoenix Valorant",
        "description": "Escuadra china con experiencia en escenarios internacionales.",
        "founded_date": "2017-12-01",
        "players": [
            ("yosemite", "Zhuo", "Wen", "China", "DUEL", True),
            ("BerLIN", "Zhang", "Bailing", "China", "CTRL", False),
            ("Autumn", "Kun", "Yang", "China", "INIT", False),
            ("ZiHao", "Zhang", "Zihao", "China", "SENT", False),
            ("AnG", "An", "Kang", "China", "FLEX", False),
        ],
        "coach": ("NaThanD", "Wang", "Nan", "China"),
        "staff": [
            ("Liu", "Chen", "analyst", "China"),
            ("Zhao", "Lin", "manager", "China"),
        ],
    },
    {
        "game": VAL, "org": "bilibili-gaming", "name": "Bilibili Gaming Valorant",
        "description": "Potencia china en Valorant con un roster consolidado.",
        "founded_date": "2017-01-01",
        "players": [
            ("whzy", "Zhang", "Wei", "China", "DUEL", True),
            ("Jing", "Li", "Jing", "China", "INIT", False),
            ("FengF", "Feng", "Jun", "China", "SENT", False),
            ("ZH1", "Zhao", "Hao", "China", "CTRL", False),
            ("Jiujiu", "Jiu", "Jiu", "China", "FLEX", False),
        ],
        "coach": ("bail", "Cheng", "Bai", "China"),
        "staff": [
            ("Sun", "Yu", "analyst", "China"),
            ("Hu", "Yan", "manager", "China"),
        ],
    },
    {
        "game": VAL, "org": "nrg", "name": "NRG Valorant",
        "description": "Organización norteamericana con roster de veteranos.",
        "founded_date": "2015-10-01",
        "players": [
            ("s0m", "Sam", "Oh", "Estados Unidos", "CTRL", True),
            ("Ethan", "Ethan", "Arnold", "Estados Unidos", "INIT", False),
            ("Crashies", "Austin", "Roberts", "Estados Unidos", "SENT", False),
            ("Victor", "Victor", "Wong", "Estados Unidos", "DUEL", False),
            ("FNS", "Pujan", "Mehta", "Estados Unidos", "FLEX", False),
        ],
        "coach": ("Chet", "Chet", "Singh", "Estados Unidos"),
        "staff": [
            ("Andrew", "Park", "analyst", "Estados Unidos"),
            ("Daniel", "Ortiz", "manager", "Estados Unidos"),
        ],
    },
    {
        "game": VAL, "org": "leviatan", "name": "Leviatán Valorant",
        "description": "Organización latinoamericana de élite en Valorant.",
        "founded_date": "2021-01-01",
        "players": [
            ("keznit", "Angelo", "Mori", "Chile", "DUEL", True),
            ("NagZ", "Nicolás", "González", "Chile", "INIT", False),
            ("Mazino", "Ignacio", "Rojas", "Chile", "CTRL", False),
            ("Melser", "Matías", "Rojas", "Chile", "SENT", False),
            ("kiNzo", "Benjamín", "Poblete", "Chile", "FLEX", False),
        ],
        "coach": ("Onur", "Onur", "Kabadayı", "Turquía"),
        "staff": [
            ("Tomás", "Rojas", "analyst", "Chile"),
            ("Camila", "Díaz", "manager", "Chile"),
        ],
    },
    # --------------------------- League of Legends -------------------------
    {
        "game": LOL, "org": "bilibili-gaming", "name": "Bilibili Gaming LoL",
        "description": "Escuadra china dominante de la LPL.",
        "founded_date": "2017-01-01",
        "players": [
            ("Bin", "Chen", "Ze-Bin", "China", "TOP", False),
            ("Xun", "Peng", "Li-xun", "China", "JNG", False),
            ("Yagao", "Zeng", "Qi", "China", "MID", True),
            ("Elk", "Zhao", "Jia-hao", "China", "ADC", False),
            ("ON", "Luo", "Wen-jun", "China", "SUPP", False),
        ],
        "coach": ("Daeny", "Yang", "Dae-in", "Corea del Sur"),
        "staff": [
            ("Wang", "Rui", "analyst", "China"),
            ("Xu", "Lei", "manager", "China"),
        ],
    },
    {
        "game": LOL, "org": "top-esports", "name": "Top Esports LoL",
        "description": "Organización china con plantilla de superestrellas.",
        "founded_date": "2017-12-01",
        "players": [
            ("Wayward", "Huang", "Ren-xing", "China", "TOP", False),
            ("Tian", "Gao", "Tian-liang", "China", "JNG", False),
            ("Creme", "Lin", "Jian", "China", "MID", True),
            ("JackeyLove", "Yu", "Wen-bo", "China", "ADC", False),
            ("Meiko", "Tian", "Ye", "China", "SUPP", False),
        ],
        "coach": ("Maokai", "Chen", "Maokai", "China"),
        "staff": [
            ("Guo", "Peng", "analyst", "China"),
            ("Li", "Na", "manager", "China"),
        ],
    },
    {
        "game": LOL, "org": "weibo-gaming", "name": "Weibo Gaming LoL",
        "description": "Escuadra china finalista mundial.",
        "founded_date": "2013-01-01",
        "players": [
            ("TheShy", "Kang", "Seung-lok", "Corea del Sur", "TOP", False),
            ("Weiwei", "Wang", "Wei", "China", "JNG", False),
            ("Xiaohu", "Li", "Yuan-Hao", "China", "MID", True),
            ("Light", "Wang", "Guang-yu", "China", "ADC", False),
            ("Crisp", "Liu", "Qing-song", "China", "SUPP", False),
        ],
        "coach": ("Kenzhu", "Zhu", "Kenzhu", "China"),
        "staff": [
            ("Feng", "Lei", "analyst", "China"),
            ("Deng", "Yu", "manager", "China"),
        ],
    },
    {
        "game": LOL, "org": "mad-lions-koi", "name": "MAD Lions KOI LoL",
        "description": "Organización europea con hinchada masiva en la LEC.",
        "founded_date": "2017-01-01",
        "players": [
            ("Chasy", "Krzysztof", "Wojciechowski", "Polonia", "TOP", False),
            ("Elyoya", "Javier", "Prades", "España", "JNG", True),
            ("Fresskowy", "Bartosz", "Prenc", "Polonia", "MID", False),
            ("Supa", "David", "Martínez", "España", "ADC", False),
            ("Alvaro", "Álvaro", "Fernández", "España", "SUPP", False),
        ],
        "coach": ("Peter Dun", "Peter", "Dun", "Reino Unido"),
        "staff": [
            ("Sergio", "Moya", "analyst", "España"),
            ("Lucía", "Gil", "manager", "España"),
        ],
    },
    {
        "game": LOL, "org": "team-vitality", "name": "Team Vitality LoL",
        "description": "El club francés más importante y campeón de la LEC.",
        "founded_date": "2013-08-05",
        "players": [
            ("Photon", "Kyung", "Gyu-tae", "Corea del Sur", "TOP", False),
            ("Lyncas", "Linas", "Nauncikas", "Lituania", "JNG", False),
            ("Vetheo", "Vincent", "Berthier", "Francia", "MID", True),
            ("Carzzy", "Patrik", "Danecek", "República Checa", "ADC", False),
            ("Hylissang", "Zdravets", "Galabov", "Bulgaria", "SUPP", False),
        ],
        "coach": ("Carter", "Carter", "Nash", "Estados Unidos"),
        "staff": [
            ("Hugo", "Martin", "analyst", "Francia"),
            ("Emma", "Dubois", "manager", "Francia"),
        ],
    },
    {
        "game": LOL, "org": "sk-gaming", "name": "SK Gaming LoL",
        "description": "Organización alemana con larga trayectoria competitiva.",
        "founded_date": "1997-01-01",
        "players": [
            ("Irrelevant", "Jakub", "Woźniak", "Polonia", "TOP", False),
            ("ISMA", "Ismael", "Boualem", "Suecia", "JNG", False),
            ("Nisqy", "Yasin", "Dinçer", "Bélgica", "MID", True),
            ("Rahel", "Rahel", "Ghumrawi", "Alemania", "ADC", False),
            ("Luon", "Norman", "Luong", "Alemania", "SUPP", False),
        ],
        "coach": ("Gevous", "Gevorg", "Arzumanyan", "Alemania"),
        "staff": [
            ("Lena", "Fischer", "analyst", "Alemania"),
            ("Tobias", "Wagner", "manager", "Alemania"),
        ],
    },
    {
        "game": LOL, "org": "kt-rolster", "name": "KT Rolster LoL",
        "description": "Escuadra coreana histórica de la LCK.",
        "founded_date": "1999-01-01",
        "players": [
            ("PerfecT", "Lee", "Seung-min", "Corea del Sur", "TOP", False),
            ("Cuzz", "Moon", "Woo-chan", "Corea del Sur", "JNG", False),
            ("Bdd", "Gwak", "Bo-seong", "Corea del Sur", "MID", True),
            ("Deft", "Kim", "Hyuk-kyu", "Corea del Sur", "ADC", False),
            ("Way", "Kim", "Ji-hoon", "Corea del Sur", "SUPP", False),
        ],
        "coach": ("Hirai", "Kang", "Do-hoon", "Corea del Sur"),
        "staff": [
            ("Seo", "Jun-ho", "analyst", "Corea del Sur"),
            ("Han", "Ji-min", "manager", "Corea del Sur"),
        ],
    },
    {
        "game": LOL, "org": "hanwha-life-esports", "name": "Hanwha Life Esports LoL",
        "description": "Equipo coreano campeón de la LCK.",
        "founded_date": "2018-01-01",
        "players": [
            ("Zeus", "Choi", "Woo-je", "Corea del Sur", "TOP", False),
            ("Peanut", "Han", "Wang-ho", "Corea del Sur", "JNG", False),
            ("Zeka", "Kim", "Geon-woo", "Corea del Sur", "MID", True),
            ("Viper", "Park", "Do-hyeon", "Corea del Sur", "ADC", False),
            ("Delight", "Yoo", "Hwan-joong", "Corea del Sur", "SUPP", False),
        ],
        "coach": ("DanDy", "Choi", "In-kyu", "Corea del Sur"),
        "staff": [
            ("Ryu", "Seung-min", "analyst", "Corea del Sur"),
            ("Shin", "Ha-eun", "manager", "Corea del Sur"),
        ],
    },
    {
        "game": LOL, "org": "dplus-kia", "name": "Dplus KIA LoL",
        "description": "Organización coreana campeona del mundo de LoL.",
        "founded_date": "2012-01-01",
        "players": [
            ("Kingen", "Hwang", "Seong-hoon", "Corea del Sur", "TOP", False),
            ("Lucid", "Choi", "Yong-hyeok", "Corea del Sur", "JNG", False),
            ("ShowMaker", "Heo", "Su", "Corea del Sur", "MID", True),
            ("Aiming", "Kim", "Ha-ram", "Corea del Sur", "ADC", False),
            ("Kellin", "Kim", "Hyeong-gyu", "Corea del Sur", "SUPP", False),
        ],
        "coach": ("Acorn", "Kim", "Dae-ho", "Corea del Sur"),
        "staff": [
            ("Baek", "Seo-yeon", "analyst", "Corea del Sur"),
            ("Noh", "Min-jae", "manager", "Corea del Sur"),
        ],
    },
    {
        "game": LOL, "org": "cloud9", "name": "Cloud9 LoL",
        "description": "Máximo referente norteamericano de la LCS.",
        "founded_date": "2013-01-01",
        "players": [
            ("Thanatos", "Park", "Seung-gyu", "Estados Unidos", "TOP", False),
            ("Blaber", "Robert", "Huang", "Canadá", "JNG", True),
            ("Jojopyun", "Joseph", "Pyun", "Canadá", "MID", False),
            ("Berserker", "Kim", "Min-cheol", "Corea del Sur", "ADC", False),
            ("Vulcan", "Philippe", "Laflamme", "Canadá", "SUPP", False),
        ],
        "coach": ("Reapered", "Bok", "Han-gyu", "Corea del Sur"),
        "staff": [
            ("Michael", "Chen", "analyst", "Estados Unidos"),
            ("Sarah", "Kim", "manager", "Estados Unidos"),
        ],
    },
]


class Command(BaseCommand):
    help = "Añade equipos de Valorant y LoL (16 por juego) y su cuerpo técnico (idempotente)."

    def handle(self, *args, **options):
        self.games = {g.slug: g for g in Game.objects.filter(slug__in=[VAL, LOL])}
        for slug in (VAL, LOL):
            if slug not in self.games:
                self.stderr.write(self.style.ERROR(f"Falta el juego '{slug}'. Carga las fixtures primero."))
                return
        self.roles = {
            slug: {r.abbreviation: r for r in game.roles.all()}
            for slug, game in self.games.items()
        }

        self._create_orgs()
        self._create_teams()
        self.stdout.write(self.style.SUCCESS(
            f"Proceso finalizado. Organizaciones: {Organization.objects.count()} · "
            f"Equipos: {Team.objects.count()} · Jugadores: {Player.objects.count()} · "
            f"Staff: {StaffMember.objects.count()}"
        ))

    # ------------------------------------------------------------------
    def _create_orgs(self):
        for slug, name, abbr, country, founded, description in ORGS:
            org, created = Organization.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "abbreviation": abbr,
                    "country": country,
                    "description": description,
                    "founded_date": founded,
                    "is_active": True,
                },
            )
            if created:
                self.stdout.write(f"  [+] Organización: {org.name}")

    # ------------------------------------------------------------------
    def _create_teams(self):
        for data in TEAMS:
            game = self.games[data["game"]]
            org = Organization.objects.get(slug=data["org"])
            team, _ = Team.objects.get_or_create(
                organization=org,
                game=game,
                name=data["name"],
                defaults={
                    "slug": slugify(data["name"]),
                    "description": data["description"],
                    "founded_date": data["founded_date"],
                    "status": Team.Status.ACTIVE,
                },
            )
            role_map = self.roles[data["game"]]
            for nick, first, last, country, role, captain in data["players"]:
                player = self._player(nick, first, last, country)
                self._assignment(player, team, role_map[role], captain)

            coach_nick, coach_first, coach_last, coach_country = data["coach"]
            coach = self._player(coach_nick, coach_first, coach_last, coach_country, ptype=Player.PlayerType.COACH)
            self._assignment(coach, team, role_map["COACH"], False)

            self._staff(coach_first, coach_last, coach_country, team, TeamStaffAssignment.Role.HEAD_COACH)
            for first, last, role, country in data["staff"]:
                self._staff(first, last, country, team, role)

    # ------------------------------------------------------------------
    def _player(self, nick, first, last, country, ptype=Player.PlayerType.PLAYER):
        player, _ = Player.objects.get_or_create(
            nickname=nick,
            defaults={
                "first_name": first,
                "last_name": last,
                "country": country,
                "player_type": ptype,
            },
        )
        return player

    def _assignment(self, player, team, role, captain):
        if PlayerTeamAssignment.objects.filter(player=player, left_at__isnull=True).exists():
            return
        PlayerTeamAssignment.objects.create(
            player=player,
            team=team,
            competitive_role=role,
            joined_at=JOINED,
            status=PlayerTeamAssignment.Status.ACTIVE,
            is_captain=captain,
        )

    def _staff(self, first, last, country, team, role):
        staff, _ = StaffMember.objects.get_or_create(
            first_name=first,
            last_name=last,
            defaults={"country": country, "email": f"{slugify(first)}.{slugify(last)}@esports.gg"},
        )
        exists = TeamStaffAssignment.objects.filter(
            staff=staff, team=team, role=role, ended_at__isnull=True
        ).exists()
        if not exists:
            TeamStaffAssignment.objects.create(
                staff=staff, team=team, role=role, started_at=STAFF_STARTED
            )
