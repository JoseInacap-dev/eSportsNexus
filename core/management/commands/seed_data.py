"""Comando para poblar la base de datos con datos iniciales (seed data).

Ejecución:
    python manage.py seed_data
"""

from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import OrganizationMembership, User
from matches.models import Match, MatchMap, StatDefinition
from organizations.models import Game, GameRole, Organization, Team
from players.models import Player, PlayerTeamAssignment
from staff.models import StaffMember, TeamStaffAssignment
from training.models import TrainingAttendance, TrainingSession


class Command(BaseCommand):
    help = "Puebla la base de datos con datos de prueba realistas para NEXUS Esports"

    def handle(self, *args, **options):
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
        val, _ = Game.objects.get_or_create(
            slug="valorant",
            defaults={
                "name": "Valorant",
                "short_name": "VAL",
                "default_team_size": 5,
            },
        )
        lol, _ = Game.objects.get_or_create(
            slug="league-of-legends",
            defaults={
                "name": "League of Legends",
                "short_name": "LoL",
                "default_team_size": 5,
            },
        )
        cs2, _ = Game.objects.get_or_create(
            slug="counter-strike-2",
            defaults={
                "name": "Counter-Strike 2",
                "short_name": "CS2",
                "default_team_size": 5,
            },
        )
        self.stdout.write(self.style.SUCCESS("  [+] Juegos registrados: Valorant, LoL, CS2"))

        # 3. Roles por Juego
        roles_data = {
            val: [
                ("Duelista", "DUEL", "Especialista en bajas tempranas y apertura de zonas."),
                ("Iniciador", "INIT", "Facilita la entrada al sitio mediante información y utilidad."),
                ("Controlador", "CTRL", "Bloquea líneas de visión mediante humos defensivos y ofensivos."),
                ("Centinela", "SENT", "Experto en anclaje y defensa de sitios con trampas."),
            ],
            lol: [
                ("Top Laner", "TOP", "Línea superior, tanque o luchador en solo lane."),
                ("Jungler", "JNG", "Control de objetivos neutrales y gankeos tempranos."),
                ("Mid Laner", "MID", "Línea central con gran impacto en daño mágico o físico."),
                ("ADC", "ADC", "Tirador principal de daño sostenido a distancia."),
                ("Support", "SUPP", "Protección, control de masas y visión estratégica."),
            ],
            cs2: [
                ("Entry Fragger", "ENTRY", "Primera línea de choque en rondas ofensivas."),
                ("AWPer", "AWP", "Tirador de precisión con rifle de francotirador."),
                ("In-Game Leader", "IGL", "Capitán táctico y estratega de rondas."),
                ("Lurker", "LURK", "Especialista en control silencioso de mapa."),
                ("Support", "SUPP", "Gestión de utilidades, flashbangs y humos de apoyo."),
            ],
        }

        created_roles = {}
        for game, roles in roles_data.items():
            for name, abbr, desc in roles:
                r, _ = GameRole.objects.get_or_create(
                    game=game,
                    name=name,
                    defaults={"abbreviation": abbr, "description": desc},
                )
                created_roles[(game.slug, name)] = r
        self.stdout.write(self.style.SUCCESS("  [+] Roles competitivos configurados"))

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
            slug="nexus-valorant",
            defaults={
                "name": "NEXUS Valorant",
                "game": val,
                "description": "Escuadra principal de Valorant participando en VCT Challengers.",
                "status": Team.Status.ACTIVE,
                "founded_date": date(2023, 3, 1),
            },
        )
        team_nxs_lol, _ = Team.objects.get_or_create(
            organization=nexus_org,
            slug="nexus-lol",
            defaults={
                "name": "NEXUS League of Legends",
                "game": lol,
                "description": "Equipo competitivo de LoL en la Liga Regional Sur.",
                "status": Team.Status.ACTIVE,
                "founded_date": date(2023, 4, 1),
            },
        )
        team_nxs_cs2, _ = Team.objects.get_or_create(
            organization=nexus_org,
            slug="nexus-cs2",
            defaults={
                "name": "NEXUS CS2",
                "game": cs2,
                "description": "Escuadra de Counter-Strike 2 en el circuito sudamericano.",
                "status": Team.Status.ACTIVE,
                "founded_date": date(2024, 1, 10),
            },
        )

        team_kru_val, _ = Team.objects.get_or_create(
            organization=kru_org,
            slug="kru-valorant",
            defaults={
                "name": "KRÜ Valorant",
                "game": val,
                "description": "Equipo oficial de Valorant de KRÜ.",
                "status": Team.Status.ACTIVE,
            },
        )
        team_lev_lol, _ = Team.objects.get_or_create(
            organization=lev_org,
            slug="leviatan-lol",
            defaults={
                "name": "Leviatán LoL",
                "game": lol,
                "description": "Escuadra de League of Legends de Leviatán.",
                "status": Team.Status.ACTIVE,
            },
        )
        self.stdout.write(self.style.SUCCESS("  [+] Equipos creados: NEXUS VAL, NEXUS LoL, NEXUS CS2 y rivales"))

        # 6. Jugadores y Asignaciones
        players_data = [
            # NEXUS Valorant
            ("Matías", "Silva", "Tenzin", "matias.silva@nexus.gg", "Chile", team_nxs_val, ("valorant", "Duelista"), 10, False),
            ("Carlos", "Vega", "Shadow", "carlos.vega@nexus.gg", "Chile", team_nxs_val, ("valorant", "Controlador"), 7, False),
            ("Ignacio", "Morales", "ViperX", "ignacio.m@nexus.gg", "Chile", team_nxs_val, ("valorant", "Centinela"), 1, True),
            ("Sebastián", "Soto", "Blaze", "sebastian.soto@nexus.gg", "Chile", team_nxs_val, ("valorant", "Iniciador"), 14, False),
            ("Felipe", "Castro", "Krono", "felipe.castro@nexus.gg", "Chile", team_nxs_val, ("valorant", "Iniciador"), 22, False),
            # NEXUS LoL
            ("Lucas", "Gómez", "Mythic", "lucas.gomez@nexus.gg", "Chile", team_nxs_lol, ("league-of-legends", "Top Laner"), 3, False),
            ("Andrés", "Torres", "Ghost", "andres.torres@nexus.gg", "Argentina", team_nxs_lol, ("league-of-legends", "Jungler"), 9, False),
            ("Joaquín", "Rivas", "Arcane", "joaquin.rivas@nexus.gg", "Chile", team_nxs_lol, ("league-of-legends", "Mid Laner"), 10, True),
            ("Diego", "Araya", "Bullet", "diego.araya@nexus.gg", "Chile", team_nxs_lol, ("league-of-legends", "ADC"), 23, False),
            ("Gonzalo", "Peña", "Oracle", "gonzalo.pena@nexus.gg", "Perú", team_nxs_lol, ("league-of-legends", "Support"), 5, False),
            # NEXUS CS2
            ("Tomás", "Vargas", "Striker", "tomas.vargas@nexus.gg", "Chile", team_nxs_cs2, ("counter-strike-2", "Entry Fragger"), 11, False),
            ("Rodrigo", "Muñoz", "SniperCL", "rodrigo.m@nexus.gg", "Chile", team_nxs_cs2, ("counter-strike-2", "AWPer"), 8, False),
            ("Gabriel", "Ortiz", "MasterMind", "gabriel.ortiz@nexus.gg", "Chile", team_nxs_cs2, ("counter-strike-2", "In-Game Leader"), 4, True),
            ("Cristóbal", "Herrera", "Smoke", "cristobal.h@nexus.gg", "Chile", team_nxs_cs2, ("counter-strike-2", "Lurker"), 17, False),
            ("Esteban", "Rojas", "Anchor", "esteban.rojas@nexus.gg", "Chile", team_nxs_cs2, ("counter-strike-2", "Support"), 6, False),
        ]

        assigned_players = []
        for fn, ln, nick, email, country, team, role_key, jersey, is_cap in players_data:
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
                    "jersey_number": jersey,
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
            away_name="9z Team",
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
            away_name="Sentinels Academy",
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
            away_name="Furious Gaming",
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
            away_name="MIBR Academy",
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
