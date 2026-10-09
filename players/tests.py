import datetime

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from organizations.models import Game, GameRole, Organization, Team
from players.models import Player, PlayerTeamAssignment


class PlayerModelTests(TestCase):
    def test_player_str_and_full_name(self):
        player = Player.objects.create(first_name="Juan", last_name="Pérez", nickname="juanpe")
        self.assertEqual(str(player), "juanpe")
        self.assertEqual(player.full_name, "Juan Pérez")


class PlayerAssignmentTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Nova", slug="nova")
        self.val = Game.objects.create(name="Valorant", slug="valorant")
        self.lol = Game.objects.create(name="League of Legends", slug="lol")
        self.role_val = GameRole.objects.create(game=self.val, name="Duelist")
        self.role_lol = GameRole.objects.create(game=self.lol, name="Top")
        self.team = Team.objects.create(
            organization=self.org, game=self.val, name="Nova Blue", slug="nova-blue"
        )
        self.player = Player.objects.create(first_name="Luis", nickname="luisito")

    def test_open_assignment_created(self):
        assignment = PlayerTeamAssignment.objects.create(
            player=self.player,
            team=self.team,
            competitive_role=self.role_val,
            joined_at=datetime.date(2026, 1, 1),
        )
        self.assertIn("luisito", str(assignment))

    def test_player_cannot_have_two_open_assignments_in_same_team(self):
        PlayerTeamAssignment.objects.create(
            player=self.player,
            team=self.team,
            joined_at=datetime.date(2026, 1, 1),
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PlayerTeamAssignment.objects.create(
                    player=self.player,
                    team=self.team,
                    joined_at=datetime.date(2026, 2, 1),
                )

    def test_rehire_is_allowed_after_closing_previous_assignment(self):
        first = PlayerTeamAssignment.objects.create(
            player=self.player,
            team=self.team,
            joined_at=datetime.date(2026, 1, 1),
            left_at=datetime.date(2026, 3, 1),
        )
        second = PlayerTeamAssignment.objects.create(
            player=self.player,
            team=self.team,
            joined_at=datetime.date(2026, 4, 1),
        )
        self.assertIsNotNone(first.pk)
        self.assertIsNotNone(second.pk)

    def test_left_at_cannot_precede_joined_at(self):
        assignment = PlayerTeamAssignment(
            player=self.player,
            team=self.team,
            joined_at=datetime.date(2026, 5, 1),
            left_at=datetime.date(2026, 1, 1),
        )
        with self.assertRaises(ValidationError):
            assignment.full_clean()

    def test_competitive_role_must_match_team_game(self):
        assignment = PlayerTeamAssignment(
            player=self.player,
            team=self.team,
            competitive_role=self.role_lol,
            joined_at=datetime.date(2026, 1, 1),
        )
        with self.assertRaises(ValidationError) as ctx:
            assignment.full_clean()
        self.assertIn("competitive_role", ctx.exception.message_dict)
