import datetime

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from organizations.models import Game, Organization, Team
from staff.models import StaffMember, TeamStaffAssignment


class TeamStaffAssignmentTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Nova", slug="nova")
        self.game = Game.objects.create(name="Valorant", slug="valorant")
        self.team = Team.objects.create(
            organization=self.org, game=self.game, name="Nova Blue", slug="nova-blue"
        )
        self.staff = StaffMember.objects.create(first_name="Marta", last_name="Ruiz")

    def test_staff_assignment_created(self):
        assignment = TeamStaffAssignment.objects.create(
            staff=self.staff,
            team=self.team,
            role=TeamStaffAssignment.Role.HEAD_COACH,
            started_at=datetime.date(2026, 1, 1),
        )
        self.assertIn("Entrenador principal", str(assignment))

    def test_cannot_have_two_open_assignments_same_role(self):
        TeamStaffAssignment.objects.create(
            staff=self.staff,
            team=self.team,
            role=TeamStaffAssignment.Role.HEAD_COACH,
            started_at=datetime.date(2026, 1, 1),
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                TeamStaffAssignment.objects.create(
                    staff=self.staff,
                    team=self.team,
                    role=TeamStaffAssignment.Role.HEAD_COACH,
                    started_at=datetime.date(2026, 2, 1),
                )

    def test_end_cannot_precede_start(self):
        assignment = TeamStaffAssignment(
            staff=self.staff,
            team=self.team,
            role=TeamStaffAssignment.Role.MANAGER,
            started_at=datetime.date(2026, 5, 1),
            ended_at=datetime.date(2026, 1, 1),
        )
        with self.assertRaises(ValidationError):
            assignment.full_clean()
