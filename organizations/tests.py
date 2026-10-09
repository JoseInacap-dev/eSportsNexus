from django.db import IntegrityError, transaction
from django.test import TestCase

from organizations.models import Game, GameRole, Organization, Team


class GameAndRoleTests(TestCase):
    def test_game_str_and_roles(self):
        game = Game.objects.create(name="Valorant", slug="valorant", short_name="VAL")
        role = GameRole.objects.create(game=game, name="Duelist")
        self.assertEqual(str(game), "Valorant")
        self.assertIn("VAL", str(role))

    def test_role_name_unique_per_game(self):
        game = Game.objects.create(name="Valorant", slug="valorant")
        GameRole.objects.create(game=game, name="Duelist")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                GameRole.objects.create(game=game, name="Duelist")


class TeamTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Nova Esports", slug="nova")
        self.game = Game.objects.create(name="Valorant", slug="valorant")

    def test_team_belongs_to_organization_and_game(self):
        team = Team.objects.create(
            organization=self.org, game=self.game, name="Nova Blue", slug="nova-blue"
        )
        self.assertEqual(team.organization, self.org)
        self.assertEqual(team.game, self.game)
        self.assertEqual(self.org.teams.count(), 1)

    def test_team_name_unique_within_org_and_game(self):
        Team.objects.create(
            organization=self.org, game=self.game, name="Nova Blue", slug="nova-blue"
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Team.objects.create(
                    organization=self.org,
                    game=self.game,
                    name="Nova Blue",
                    slug="nova-blue-2",
                )
