from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from organizations.models import Game, Organization, Team
from players.models import Player
from training.models import TrainingAttendance, TrainingSession


class TrainingTests(TestCase):
    def setUp(self):
        org = Organization.objects.create(name="Nova", slug="nova")
        game = Game.objects.create(name="Valorant", slug="valorant")
        self.team = Team.objects.create(
            organization=org, game=game, name="Nova Blue", slug="nova-blue"
        )
        self.session = TrainingSession.objects.create(
            team=self.team, title="Scrim bloque", scheduled_at=timezone.now()
        )
        self.player = Player.objects.create(first_name="Luis", nickname="luisito")

    def test_session_str(self):
        self.assertIn("Scrim bloque", str(self.session))

    def test_attendance_unique_per_session(self):
        TrainingAttendance.objects.create(session=self.session, player=self.player)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                TrainingAttendance.objects.create(
                    session=self.session, player=self.player
                )
