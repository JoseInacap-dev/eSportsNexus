from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import OrganizationMembership
from matches.models import Match
from organizations.models import Game, Organization, Team
from players.models import Player, PlayerTeamAssignment

User = get_user_model()


class BaseFixture(TestCase):
    def setUp(self):
        self.outsider = User.objects.create_user(
            username="outsider", email="o@example.com", password="pass12345"
        )
        self.viewer = User.objects.create_user(
            username="viewer", email="v@example.com", password="pass12345"
        )
        self.manager = User.objects.create_user(
            username="manager", email="m@example.com", password="pass12345"
        )
        self.org = Organization.objects.create(
            name="Nova Esports", slug="nova", abbreviation="NOVA"
        )
        self.other_org = Organization.objects.create(
            name="Otra Org", slug="otra", abbreviation="OTRA"
        )
        self.game = Game.objects.create(
            name="Valorant", slug="valorant", short_name="VAL"
        )
        self.team = Team.objects.create(
            organization=self.org,
            game=self.game,
            name="Nova Blue",
        )
        self.team2 = Team.objects.create(
            organization=self.org,
            game=self.game,
            name="Nova Red",
        )
        self.other_team = Team.objects.create(
            organization=self.other_org,
            game=self.game,
            name="Otra Blue",
        )
        OrganizationMembership.objects.create(
            user=self.viewer,
            organization=self.org,
            role=OrganizationMembership.Role.VIEWER,
        )
        OrganizationMembership.objects.create(
            user=self.manager,
            organization=self.org,
            role=OrganizationMembership.Role.ADMIN,
        )


class HomeViewTests(BaseFixture):
    def test_home_is_public(self):
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Esports Manager")


class TeamHtmlViewTests(BaseFixture):
    def test_list_requires_login(self):
        response = self.client.get(reverse("organizations:team-list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_list_is_scoped_by_membership(self):
        self.client.force_login(self.outsider)
        response = self.client.get(reverse("organizations:team-list"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Nova Blue")

        self.client.force_login(self.viewer)
        response = self.client.get(reverse("organizations:team-list"))
        self.assertContains(response, "Nova Blue")

    def test_detail_denied_for_outsider(self):
        self.client.force_login(self.outsider)
        response = self.client.get(
            reverse("organizations:team-detail", args=[self.team.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_detail_allowed_for_members(self):
        self.client.force_login(self.viewer)
        response = self.client.get(
            reverse("organizations:team-detail", args=[self.team.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nova Blue")

    def test_viewer_cannot_create_team(self):
        self.client.force_login(self.viewer)
        response = self.client.post(
            reverse("organizations:team-create"),
            {
                "organization": self.org.pk,
                "game": self.game.pk,
                "name": "Nova Academy",
                "status": Team.Status.ACTIVE,
            },
        )
        # El formulario restringe las organizaciones gestionables, por lo que
        # valida en la capa de formulario (200 con errores) o en la vista (403).
        self.assertIn(response.status_code, (200, 403))
        self.assertFalse(Team.objects.filter(name="Nova Academy").exists())

    def test_manager_can_create_team(self):
        self.client.force_login(self.manager)
        response = self.client.post(
            reverse("organizations:team-create"),
            {
                "organization": self.org.pk,
                "game": self.game.pk,
                "name": "Nova Academy",
                "status": Team.Status.ACTIVE,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Team.objects.filter(name="Nova Academy").exists())


class PlayerAndMatchViewsTests(BaseFixture):
    def test_player_create_requires_managing_role(self):
        self.client.force_login(self.viewer)
        response = self.client.post(
            reverse("players:player-create"),
            {
                "first_name": "Ana",
                "last_name": "Paz",
                "nickname": "anapaz",
                "player_type": "player",
            },
        )
        self.assertEqual(response.status_code, 403)

        self.client.force_login(self.manager)
        response = self.client.post(
            reverse("players:player-create"),
            {
                "first_name": "Ana",
                "last_name": "Paz",
                "nickname": "anapaz",
                "player_type": "player",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Player.objects.filter(nickname="anapaz").exists())

    def test_match_list_scoped(self):
        Match.objects.create(
            game=self.game,
            home_team=self.team,
            away_team=self.team2,
            scheduled_at="2026-01-01T18:00:00Z",
        )
        Match.objects.create(
            game=self.game,
            home_team=self.other_team,
            away_team=self.team2,
            scheduled_at="2026-01-02T18:00:00Z",
        )
        self.client.force_login(self.manager)
        response = self.client.get(reverse("matches:match-list"))
        self.assertContains(response, "Nova Red")
        self.assertNotContains(response, "Otra Blue")


class ApiTests(BaseFixture):
    def setUp(self):
        super().setUp()
        self.api = APIClient()

    def test_api_requires_authentication(self):
        response = self.api.get("/api/teams/")
        self.assertEqual(response.status_code, 403)

    def test_api_team_list_scoped(self):
        self.api.force_authenticate(user=self.manager)
        response = self.api.get("/api/teams/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 2)
        self.assertEqual(data["results"][0]["name"], "Nova Blue")

    def test_api_create_team_forbidden_for_outsider(self):
        self.api.force_authenticate(user=self.outsider)
        response = self.api.post(
            "/api/teams/",
            {
                "organization": self.org.pk,
                "game": self.game.pk,
                "name": "Nova Academy",
                "slug": "nova-academy",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_api_manager_can_create_team(self):
        self.api.force_authenticate(user=self.manager)
        response = self.api.post(
            "/api/teams/",
            {
                "organization": self.org.pk,
                "game": self.game.pk,
                "name": "Nova Academy",
                "slug": "nova-academy",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)

    def test_api_players_list(self):
        self.api.force_authenticate(user=self.manager)
        response = self.api.get("/api/players/")
        self.assertEqual(response.status_code, 200)

    def test_api_outer_cannot_read_other_org_team_detail(self):
        self.api.force_authenticate(user=self.manager)
        detail = self.api.get(f"/api/teams/{self.other_team.pk}/")
        self.assertEqual(detail.status_code, 404)


class DetailTemplatesTests(BaseFixture):
    def setUp(self):
        super().setUp()
        self.match = Match.objects.create(
            game=self.game,
            home_team=self.team,
            away_team=self.team2,
            scheduled_at="2026-01-01T18:00:00Z",
            status=Match.Status.FINISHED,
            home_score=2,
            away_score=1,
        )
        self.player = Player.objects.create(
            first_name="Ana", last_name="Paz", nickname="anapaz"
        )

    def test_match_detail_renders(self):
        self.client.force_login(self.manager)
        response = self.client.get(
            reverse("matches:match-detail", args=[self.match.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nova Red")

    def test_player_detail_renders(self):
        self.client.force_login(self.manager)
        response = self.client.get(
            reverse("players:player-detail", args=[self.player.pk])
        )
        self.assertEqual(response.status_code, 200)

    def test_training_list_and_form_render(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("training:session-list"))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse("training:session-create"))
        self.assertEqual(response.status_code, 200)

    def test_team_form_render(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("organizations:team-create"))
        self.assertEqual(response.status_code, 200)


class SeedProTeamsTests(TestCase):
    def _seed(self):
        call_command("seed_data", "--pro-teams", verbosity=0)

    def test_creates_ten_teams_split_five_and_five(self):
        self._seed()
        teams = Team.objects.filter(
            name__in=[
                "Gen.G LoL",
                "JD Gaming LoL",
                "G2 Esports LoL",
                "Fnatic LoL",
                "Team Liquid LoL",
                "Sentinels Valorant",
                "Paper Rex Valorant",
                "LOUD Valorant",
                "Fnatic Valorant",
                "G2 Esports Valorant",
            ]
        )
        self.assertEqual(teams.count(), 10)
        self.assertEqual(
            teams.filter(game__slug="league-of-legends").count(), 5
        )
        self.assertEqual(teams.filter(game__slug="valorant").count(), 5)

    def test_each_team_has_five_players_and_one_coach(self):
        self._seed()
        for team in Team.objects.all():
            open_assignments = team.player_assignments.filter(
                left_at__isnull=True
            )
            self.assertEqual(open_assignments.count(), 6)
            self.assertEqual(
                open_assignments.filter(competitive_role__name="Coach").count(),
                1,
            )

    def test_multigame_orgs_reuse_single_organization(self):
        self._seed()
        for slug in ("fnatic", "g2-esports"):
            org = Organization.objects.get(slug=slug)
            self.assertEqual(org.teams.count(), 2)

    def test_command_is_idempotent(self):
        self._seed()
        self._seed()
        self.assertEqual(Organization.objects.count(), 8)
        self.assertEqual(Team.objects.count(), 10)
        self.assertEqual(
            PlayerTeamAssignment.objects.filter(
                competitive_role__name="Coach", left_at__isnull=True
            ).count(),
            10,
        )

    def test_players_are_created_once(self):
        self._seed()
        self._seed()
        self.assertEqual(
            Player.objects.filter(nickname="Chovy").count(), 1
        )