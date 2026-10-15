import datetime

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from accounts.models import OrganizationMembership, User
from organizations.models import Game, GameRole, Organization, Team
from players.forms import PlayerTeamAssignmentForm
from players.models import Player, PlayerTeamAssignment


class PlayerModelTests(TestCase):
    def test_player_str_and_full_name(self):
        player = Player.objects.create(first_name="Juan", last_name="Pérez", nickname="juanpe")
        self.assertEqual(str(player), "juanpe")
        self.assertEqual(player.full_name, "Juan Pérez")


class PlayerAssignmentTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Nova", slug="nova", abbreviation="NOVA"
        )
        self.val = Game.objects.create(name="Valorant", slug="valorant")
        self.lol = Game.objects.create(name="League of Legends", slug="lol")
        self.role_val = GameRole.objects.create(game=self.val, name="Duelist")
        self.role_lol = GameRole.objects.create(game=self.lol, name="Top")
        self.team = Team.objects.create(
            organization=self.org, game=self.val, name="Nova Blue"
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

    def test_player_cannot_have_two_open_assignments_in_different_teams(self):
        other_team = Team.objects.create(
            organization=self.org, game=self.val, name="Nova White"
        )
        PlayerTeamAssignment.objects.create(
            player=self.player,
            team=self.team,
            joined_at=datetime.date(2026, 1, 1),
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PlayerTeamAssignment.objects.create(
                    player=self.player,
                    team=other_team,
                    joined_at=datetime.date(2026, 2, 1),
                )

    def test_clean_rejects_second_open_assignment(self):
        PlayerTeamAssignment.objects.create(
            player=self.player,
            team=self.team,
            joined_at=datetime.date(2026, 1, 1),
        )
        other_team = Team.objects.create(
            organization=self.org, game=self.val, name="Nova White"
        )
        assignment = PlayerTeamAssignment(
            player=self.player,
            team=other_team,
            joined_at=datetime.date(2026, 2, 1),
        )
        with self.assertRaises(ValidationError) as ctx:
            assignment.full_clean()
        self.assertIn("player", ctx.exception.message_dict)

    def test_team_cannot_have_two_open_captains(self):
        other_player = Player.objects.create(
            first_name="Ana", nickname="anita"
        )
        PlayerTeamAssignment.objects.create(
            player=self.player,
            team=self.team,
            joined_at=datetime.date(2026, 1, 1),
            is_captain=True,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PlayerTeamAssignment.objects.create(
                    player=other_player,
                    team=self.team,
                    joined_at=datetime.date(2026, 2, 1),
                    is_captain=True,
                )

    def test_clean_rejects_second_open_captain(self):
        other_player = Player.objects.create(
            first_name="Ana", nickname="anita"
        )
        PlayerTeamAssignment.objects.create(
            player=self.player,
            team=self.team,
            joined_at=datetime.date(2026, 1, 1),
            is_captain=True,
        )
        assignment = PlayerTeamAssignment(
            player=other_player,
            team=self.team,
            joined_at=datetime.date(2026, 2, 1),
            is_captain=True,
        )
        with self.assertRaises(ValidationError) as ctx:
            assignment.full_clean()
        self.assertIn("is_captain", ctx.exception.message_dict)

    def test_new_captain_allowed_after_previous_left(self):
        other_player = Player.objects.create(
            first_name="Ana", nickname="anita"
        )
        PlayerTeamAssignment.objects.create(
            player=self.player,
            team=self.team,
            joined_at=datetime.date(2026, 1, 1),
            left_at=datetime.date(2026, 3, 1),
            is_captain=True,
        )
        assignment = PlayerTeamAssignment.objects.create(
            player=other_player,
            team=self.team,
            joined_at=datetime.date(2026, 4, 1),
            is_captain=True,
        )
        self.assertIsNotNone(assignment.pk)


class PlayerAssignmentFormTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Nova", slug="nova", abbreviation="NOVA"
        )
        self.val = Game.objects.create(name="Valorant", slug="valorant")
        self.lol = Game.objects.create(name="League of Legends", slug="lol")
        self.role_val = GameRole.objects.create(game=self.val, name="Duelist")
        self.role_lol = GameRole.objects.create(game=self.lol, name="Top")
        self.team = Team.objects.create(
            organization=self.org, game=self.val, name="Nova Blue"
        )
        self.player = Player.objects.create(first_name="Luis", nickname="luisito")

    def _team_data(self, **overrides):
        data = {
            "player": "",
            "competitive_role": self.role_val.pk,
            "joined_at": "2026-01-01",
            "status": "active",
            "is_captain": False,
            "notes": "",
            "new_player_first_name": "",
            "new_player_last_name": "",
            "new_player_nickname": "",
            "new_player_country": "",
        }
        data.update(overrides)
        return data

    def test_team_form_adds_existing_player(self):
        form = PlayerTeamAssignmentForm(
            data=self._team_data(player=self.player.pk),
            team=self.team,
        )
        self.assertTrue(form.is_valid(), form.errors)
        assignment = form.save()
        self.assertEqual(assignment.team, self.team)
        self.assertEqual(assignment.player, self.player)

    def test_team_form_creates_new_player(self):
        form = PlayerTeamAssignmentForm(
            data=self._team_data(
                new_player_first_name="Ana", new_player_nickname="anita"
            ),
            team=self.team,
        )
        self.assertTrue(form.is_valid(), form.errors)
        assignment = form.save()
        self.assertEqual(assignment.player.nickname, "anita")
        self.assertEqual(assignment.team, self.team)
        self.assertEqual(assignment.player.player_type, Player.PlayerType.PLAYER)

    def test_team_form_requires_player_or_new(self):
        form = PlayerTeamAssignmentForm(data=self._team_data(), team=self.team)
        self.assertFalse(form.is_valid())
        self.assertIn("player", form.errors)

    def test_team_form_rejects_both_existing_and_new(self):
        form = PlayerTeamAssignmentForm(
            data=self._team_data(
                player=self.player.pk,
                new_player_first_name="Ana",
                new_player_nickname="anita",
            ),
            team=self.team,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("player", form.errors)

    def test_team_form_role_scoped_to_team_game(self):
        form = PlayerTeamAssignmentForm(team=self.team)
        roles = form.fields["competitive_role"].queryset
        self.assertIn(self.role_val, roles)
        self.assertNotIn(self.role_lol, roles)

    def test_team_form_excludes_players_with_open_assignment(self):
        PlayerTeamAssignment.objects.create(
            player=self.player,
            team=self.team,
            joined_at=datetime.date(2026, 1, 1),
        )
        form = PlayerTeamAssignmentForm(team=self.team)
        self.assertNotIn(self.player, form.fields["player"].queryset)

    def test_team_form_rejects_second_captain(self):
        other_player = Player.objects.create(
            first_name="Ana", nickname="anita"
        )
        PlayerTeamAssignment.objects.create(
            player=self.player,
            team=self.team,
            joined_at=datetime.date(2026, 1, 1),
            is_captain=True,
        )
        form = PlayerTeamAssignmentForm(
            data=self._team_data(player=other_player.pk, is_captain=True),
            team=self.team,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("is_captain", form.errors)

    def test_player_form_assigns_to_team(self):
        form = PlayerTeamAssignmentForm(
            data={
                "team": self.team.pk,
                "competitive_role": self.role_val.pk,
                "joined_at": "2026-01-01",
                "status": "active",
                "is_captain": False,
                "notes": "",
            },
            player=self.player,
        )
        self.assertTrue(form.is_valid(), form.errors)
        assignment = form.save()
        self.assertEqual(assignment.player, self.player)
        self.assertEqual(assignment.team, self.team)

    def test_player_form_hides_player_and_new_fields(self):
        form = PlayerTeamAssignmentForm(player=self.player)
        self.assertNotIn("player", form.fields)
        self.assertNotIn("new_player_nickname", form.fields)

    def test_player_form_rejects_role_from_other_game(self):
        form = PlayerTeamAssignmentForm(
            data={
                "team": self.team.pk,
                "competitive_role": self.role_lol.pk,
                "joined_at": "2026-01-01",
                "status": "active",
            },
            player=self.player,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("competitive_role", form.errors)


class PlayerAssignmentViewTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Nova", slug="nova", abbreviation="NOVA"
        )
        self.other_org = Organization.objects.create(
            name="Furia", slug="furia", abbreviation="FURIA"
        )
        self.val = Game.objects.create(name="Valorant", slug="valorant")
        self.role_val = GameRole.objects.create(game=self.val, name="Duelist")
        self.team = Team.objects.create(
            organization=self.org, game=self.val, name="Nova Blue"
        )
        self.other_team = Team.objects.create(
            organization=self.other_org, game=self.val, name="Furia Black"
        )
        self.player = Player.objects.create(first_name="Luis", nickname="luisito")
        self.manager = self._make_member(self.org, "manager")
        self.outsider = User.objects.create_user(
            username="outsider",
            email="outsider@example.com",
            password="pass12345",
        )

    def _make_member(self, organization, username, role=OrganizationMembership.Role.OWNER):
        user = User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="pass12345",
        )
        OrganizationMembership.objects.create(
            user=user, organization=organization, role=role, is_active=True
        )
        return user

    def _post_data(self, **overrides):
        data = {
            "player": self.player.pk,
            "competitive_role": self.role_val.pk,
            "joined_at": "2026-01-01",
            "status": "active",
            "is_captain": False,
            "notes": "",
            "new_player_first_name": "",
            "new_player_last_name": "",
            "new_player_nickname": "",
            "new_player_country": "",
        }
        data.update(overrides)
        return data

    def test_manager_adds_player_to_team(self):
        self.client.force_login(self.manager)
        response = self.client.post(
            reverse("players:team-assignment-create", args=[self.team.pk]),
            self._post_data(),
        )
        self.assertRedirects(
            response,
            reverse("organizations:team-detail", args=[self.team.pk]),
        )
        self.assertTrue(
            PlayerTeamAssignment.objects.filter(
                player=self.player, team=self.team, left_at__isnull=True
            ).exists()
        )

    def test_non_manager_cannot_add_player_to_team(self):
        self.client.force_login(self.outsider)
        response = self.client.get(
            reverse("players:team-assignment-create", args=[self.team.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_manager_assigns_player_to_team(self):
        self.client.force_login(self.manager)
        response = self.client.post(
            reverse(
                "players:player-assignment-create", args=[self.player.pk]
            ),
            {
                "team": self.team.pk,
                "competitive_role": self.role_val.pk,
                "joined_at": "2026-01-01",
                "status": "active",
                "is_captain": False,
                "notes": "",
            },
        )
        self.assertRedirects(
            response,
            reverse("players:player-detail", args=[self.player.pk]),
        )
        self.assertTrue(
            PlayerTeamAssignment.objects.filter(
                player=self.player, team=self.team
            ).exists()
        )

    def test_outsider_cannot_assign_to_foreign_team(self):
        self.client.force_login(self.outsider)
        response = self.client.post(
            reverse(
                "players:player-assignment-create", args=[self.player.pk]
            ),
            {
                "team": self.team.pk,
                "joined_at": "2026-01-01",
                "status": "active",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            PlayerTeamAssignment.objects.filter(player=self.player).exists()
        )

    def test_finish_assignment_sets_left_at_and_status(self):
        assignment = PlayerTeamAssignment.objects.create(
            player=self.player,
            team=self.team,
            joined_at=datetime.date(2026, 1, 1),
        )
        self.client.force_login(self.manager)
        response = self.client.post(
            reverse("players:assignment-finish", args=[assignment.pk]),
            {"left_at": "2026-03-01"},
        )
        self.assertRedirects(
            response,
            reverse("organizations:team-detail", args=[self.team.pk]),
        )
        assignment.refresh_from_db()
        self.assertEqual(assignment.left_at, datetime.date(2026, 3, 1))
        self.assertEqual(assignment.status, PlayerTeamAssignment.Status.LEFT)

    def test_non_manager_cannot_finish_assignment(self):
        assignment = PlayerTeamAssignment.objects.create(
            player=self.player,
            team=self.team,
            joined_at=datetime.date(2026, 1, 1),
        )
        self.client.force_login(self.outsider)
        response = self.client.get(
            reverse("players:assignment-finish", args=[assignment.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_finish_page_renders_for_manager(self):
        assignment = PlayerTeamAssignment.objects.create(
            player=self.player,
            team=self.team,
            joined_at=datetime.date(2026, 1, 1),
        )
        self.client.force_login(self.manager)
        response = self.client.get(
            reverse("players:assignment-finish", args=[assignment.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dar de baja")


class PlayerListViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="viewer", email="viewer@example.com", password="pass12345"
        )
        self.org = Organization.objects.create(
            name="Nova", slug="nova", abbreviation="NOVA"
        )
        self.val = Game.objects.create(name="Valorant", slug="valorant")
        self.team_alpha = Team.objects.create(
            organization=self.org, game=self.val, name="Alpha"
        )
        self.team_beta = Team.objects.create(
            organization=self.org, game=self.val, name="Beta"
        )
        self.role_controller = GameRole.objects.create(
            game=self.val, name="Controller"
        )
        self.role_duelist = GameRole.objects.create(game=self.val, name="Duelist")
        self.coach = Player.objects.create(
            first_name="A",
            nickname="zeta",
            country="Chile",
            player_type=Player.PlayerType.COACH,
        )
        self.starter = Player.objects.create(
            first_name="B",
            nickname="alfa",
            country="Argentina",
            player_type=Player.PlayerType.PLAYER,
        )
        self.free_agent = Player.objects.create(
            first_name="C",
            nickname="mike",
            country="",
            player_type=Player.PlayerType.ANALYST,
        )
        PlayerTeamAssignment.objects.create(
            player=self.coach,
            team=self.team_beta,
            competitive_role=self.role_controller,
            status=PlayerTeamAssignment.Status.BENCH,
            joined_at=datetime.date(2026, 1, 1),
        )
        PlayerTeamAssignment.objects.create(
            player=self.starter,
            team=self.team_alpha,
            competitive_role=self.role_duelist,
            status=PlayerTeamAssignment.Status.ACTIVE,
            joined_at=datetime.date(2026, 1, 1),
        )
        self.url = reverse("players:player-list")
        self.client.force_login(self.user)

    def _nicknames(self, response):
        return [player.nickname for player in response.context["jugadores"]]

    def test_default_order_is_nickname_asc(self):
        response = self.client.get(self.url)
        self.assertEqual(self._nicknames(response), ["alfa", "mike", "zeta"])

    def test_order_by_nickname_desc(self):
        response = self.client.get(self.url, {"orden": "nickname", "dir": "desc"})
        self.assertEqual(self._nicknames(response), ["zeta", "mike", "alfa"])

    def test_order_by_country_puts_blanks_last(self):
        response = self.client.get(self.url, {"orden": "pais"})
        self.assertEqual(self._nicknames(response), ["alfa", "zeta", "mike"])

    def test_order_by_team_puts_free_agents_last(self):
        response = self.client.get(self.url, {"orden": "equipo"})
        self.assertEqual(self._nicknames(response), ["alfa", "zeta", "mike"])

    def test_order_by_type_follows_declared_order(self):
        response = self.client.get(self.url, {"orden": "tipo"})
        self.assertEqual(self._nicknames(response), ["alfa", "zeta", "mike"])

    def test_order_by_role_asc_puts_unassigned_last(self):
        response = self.client.get(self.url, {"orden": "rol"})
        self.assertEqual(self._nicknames(response), ["zeta", "alfa", "mike"])

    def test_order_by_role_desc_keeps_unassigned_last(self):
        response = self.client.get(self.url, {"orden": "rol", "dir": "desc"})
        self.assertEqual(self._nicknames(response), ["alfa", "zeta", "mike"])

    def test_order_by_status_follows_declared_order(self):
        response = self.client.get(self.url, {"orden": "estado"})
        self.assertEqual(self._nicknames(response), ["alfa", "zeta", "mike"])

    def test_order_by_status_desc_keeps_free_agents_last(self):
        response = self.client.get(self.url, {"orden": "estado", "dir": "desc"})
        self.assertEqual(self._nicknames(response), ["zeta", "alfa", "mike"])

    def test_nickname_order_is_case_insensitive(self):
        Player.objects.all().delete()
        Player.objects.create(first_name="X", nickname="Bravo")
        Player.objects.create(first_name="Y", nickname="alpha")
        Player.objects.create(first_name="Z", nickname="Zulu")
        response = self.client.get(self.url, {"orden": "nickname"})
        self.assertEqual(self._nicknames(response), ["alpha", "Bravo", "Zulu"])

    def test_invalid_sort_parameters_fall_back_to_default(self):
        response = self.client.get(self.url, {"orden": "bogus", "dir": "sideways"})
        self.assertEqual(self._nicknames(response), ["alfa", "mike", "zeta"])

    def test_sort_links_preserve_active_filters(self):
        response = self.client.get(self.url, {"equipo": self.team_alpha.pk})
        url = response.context["sort"]["links"]["nickname"]["url"]
        self.assertIn(f"equipo={self.team_alpha.pk}", url)
        self.assertIn("orden=nickname", url)

    def test_active_sort_link_toggles_direction(self):
        response = self.client.get(self.url, {"orden": "nickname", "dir": "asc"})
        self.assertEqual(response.context["sort"]["links"]["nickname"]["icon"], "bi-caret-up-fill")
        response = self.client.get(self.url, {"orden": "nickname", "dir": "desc"})
        self.assertEqual(response.context["sort"]["links"]["nickname"]["icon"], "bi-caret-down-fill")

