import datetime
import json

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from matches.models import (
    Match,
    MatchMap,
    PlayerMatchStat,
    StatDefinition,
    TeamMatchStat,
    Tournament,
    TournamentParticipant,
)
from organizations.models import Game, Organization, Team
from players.models import Player


class MatchConstraintsTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Nova", slug="nova", abbreviation="NOVA"
        )
        self.game = Game.objects.create(name="Valorant", slug="valorant")
        self.team_a = Team.objects.create(
            organization=self.org, game=self.game, name="Nova Blue"
        )
        self.team_b = Team.objects.create(
            organization=self.org, game=self.game, name="Nova Red"
        )
        self.when = timezone.now()

    def _match(self, **kwargs):
        defaults = dict(
            game=self.game,
            home_team=self.team_a,
            away_team=self.team_b,
            scheduled_at=self.when,
        )
        defaults.update(kwargs)
        return Match(**defaults)

    def test_match_created_and_str(self):
        match = self._match()
        match.full_clean()
        match.save()
        self.assertIn("Nova Blue", str(match))

    def test_teams_must_differ(self):
        match = self._match(away_team=self.team_a)
        with self.assertRaises(ValidationError):
            match.full_clean()

    def test_away_team_is_required(self):
        match = self._match(away_team=None)
        with self.assertRaises(ValidationError) as ctx:
            match.full_clean()
        self.assertIn("away_team", ctx.exception.message_dict)

    def test_finished_match_requires_scores(self):
        match = self._match(status=Match.Status.FINISHED)
        with self.assertRaises(ValidationError):
            match.full_clean()

    def test_finished_match_with_scores_is_valid(self):
        match = self._match(
            status=Match.Status.FINISHED, home_score=2, away_score=1
        )
        match.full_clean()
        match.save()
        self.assertEqual(match.home_score, 2)

    def test_team_must_belong_to_match_game(self):
        other_game = Game.objects.create(name="League of Legends", slug="lol")
        other_team = Team.objects.create(
            organization=self.org, game=other_game, name="Nova LoL"
        )
        match = self._match(home_team=other_team)
        with self.assertRaises(ValidationError) as ctx:
            match.full_clean()
        self.assertIn("home_team", ctx.exception.message_dict)

    def test_tournament_requires_enrolled_teams(self):
        tournament = Tournament.objects.create(
            name="Copa Nexus", game=self.game, participants_count=2
        )
        TournamentParticipant.objects.create(
            tournament=tournament, team=self.team_a
        )
        match = self._match(tournament=tournament)
        with self.assertRaises(ValidationError) as ctx:
            match.full_clean()
        self.assertIn("away_team", ctx.exception.message_dict)
        self.assertNotIn("home_team", ctx.exception.message_dict)

    def test_tournament_with_enrolled_teams_is_valid(self):
        tournament = Tournament.objects.create(
            name="Copa Nexus", game=self.game, participants_count=2
        )
        TournamentParticipant.objects.create(
            tournament=tournament, team=self.team_a
        )
        TournamentParticipant.objects.create(
            tournament=tournament, team=self.team_b
        )
        match = self._match(tournament=tournament)
        match.full_clean()
        match.save()
        self.assertEqual(match.tournament, tournament)


class TournamentModelTests(TestCase):
    def setUp(self):
        org = Organization.objects.create(
            name="Nova", slug="nova", abbreviation="NOVA"
        )
        self.game = Game.objects.create(name="Valorant", slug="valorant")
        self.other_game = Game.objects.create(name="League of Legends", slug="lol")

    def test_slug_generated_and_unique(self):
        t1 = Tournament.objects.create(
            name="Copa Nexus", game=self.game, participants_count=8
        )
        t2 = Tournament.objects.create(
            name="Copa Nexus", game=self.other_game, participants_count=8
        )
        self.assertEqual(t1.slug, "copa-nexus")
        self.assertNotEqual(t2.slug, t1.slug)
        self.assertTrue(t2.slug.startswith("copa-nexus"))

    def test_name_unique_per_game(self):
        Tournament.objects.create(name="Copa Nexus", game=self.game)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Tournament.objects.create(name="Copa Nexus", game=self.game)

    def test_image_display_priorities(self):
        t = Tournament.objects.create(
            name="Liga", game=self.game, image_url="http://example.com/logo.png"
        )
        self.assertEqual(t.image_display, "http://example.com/logo.png")

    def test_participants_count_minimum(self):
        t = Tournament(name="X", game=self.game, participants_count=1)
        with self.assertRaises(ValidationError):
            t.full_clean()



class MatchMapTests(TestCase):
    def setUp(self):
        org = Organization.objects.create(
            name="Nova", slug="nova", abbreviation="NOVA"
        )
        game = Game.objects.create(name="Valorant", slug="valorant")
        self.team = Team.objects.create(
            organization=org, game=game, name="Nova Blue"
        )
        self.team_b = Team.objects.create(
            organization=org, game=game, name="Nova Red"
        )
        self.match = Match.objects.create(
            game=game,
            home_team=self.team,
            away_team=self.team_b,
            scheduled_at=timezone.now(),
        )

    def test_map_order_unique_per_match(self):
        MatchMap.objects.create(match=self.match, order=1, map_name="Ascent")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                MatchMap.objects.create(match=self.match, order=1, map_name="Haven")


class StatDefinitionTests(TestCase):
    def test_code_unique_per_game_and_scope(self):
        game = Game.objects.create(name="Valorant", slug="valorant")
        StatDefinition.objects.create(
            game=game, scope=StatDefinition.Scope.PLAYER, code="kills", name="Kills"
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                StatDefinition.objects.create(
                    game=game,
                    scope=StatDefinition.Scope.PLAYER,
                    code="kills",
                    name="Kills (dup)",
                )


class MatchStatTests(TestCase):
    def setUp(self):
        org = Organization.objects.create(
            name="Nova", slug="nova", abbreviation="NOVA"
        )
        game = Game.objects.create(name="Valorant", slug="valorant")
        self.team = Team.objects.create(
            organization=org, game=game, name="Nova Blue"
        )
        self.team_b = Team.objects.create(
            organization=org, game=game, name="Nova Red"
        )
        self.match = Match.objects.create(
            game=game,
            home_team=self.team,
            away_team=self.team_b,
            scheduled_at=timezone.now(),
        )
        self.player = Player.objects.create(first_name="Luis", nickname="luisito")
        self.player_stat = StatDefinition.objects.create(
            game=game, scope=StatDefinition.Scope.PLAYER, code="kills", name="Kills"
        )
        self.team_stat = StatDefinition.objects.create(
            game=game, scope=StatDefinition.Scope.TEAM, code="rounds", name="Rondas ganadas"
        )

    def test_player_stat_unique_per_match(self):
        PlayerMatchStat.objects.create(
            match=self.match, player=self.player, definition=self.player_stat, value=20
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PlayerMatchStat.objects.create(
                    match=self.match,
                    player=self.player,
                    definition=self.player_stat,
                    value=25,
                )

    def test_player_stat_rejects_team_scope_definition(self):
        stat = PlayerMatchStat(
            match=self.match, player=self.player, definition=self.team_stat, value=5
        )
        with self.assertRaises(ValidationError) as ctx:
            stat.full_clean()
        self.assertIn("definition", ctx.exception.message_dict)

    def test_team_stat_rejects_player_scope_definition(self):
        stat = TeamMatchStat(
            match=self.match, team=self.team, definition=self.player_stat, value=5
        )
        with self.assertRaises(ValidationError) as ctx:
            stat.full_clean()
        self.assertIn("definition", ctx.exception.message_dict)

    def test_valid_team_stat(self):
        stat = TeamMatchStat(
            match=self.match, team=self.team, definition=self.team_stat, value=13
        )
        stat.full_clean()
        stat.save()
        self.assertEqual(str(stat).count("13"), 1)


class MatchLiveScoreTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model

        from accounts.models import OrganizationMembership

        User = get_user_model()
        self.manager = User.objects.create_user(
            username="manager", email="m@example.com", password="pass12345"
        )
        self.viewer = User.objects.create_user(
            username="viewer", email="v@example.com", password="pass12345"
        )
        self.outsider = User.objects.create_user(
            username="outsider", email="o@example.com", password="pass12345"
        )
        self.org = Organization.objects.create(
            name="Nova", slug="nova", abbreviation="NOVA"
        )
        self.other_org = Organization.objects.create(
            name="Otra", slug="otra", abbreviation="OTRA"
        )
        game = Game.objects.create(name="Valorant", slug="valorant")
        self.team = Team.objects.create(
            organization=self.org, game=game, name="Nova Blue"
        )
        self.rival = Team.objects.create(
            organization=self.other_org, game=game, name="Otra Red"
        )
        OrganizationMembership.objects.create(
            user=self.manager,
            organization=self.org,
            role=OrganizationMembership.Role.ADMIN,
        )
        OrganizationMembership.objects.create(
            user=self.viewer,
            organization=self.org,
            role=OrganizationMembership.Role.VIEWER,
        )
        self.match = Match.objects.create(
            game=game,
            home_team=self.team,
            away_team=self.rival,
            scheduled_at=timezone.now(),
        )
        self.url = reverse("matches:match-score-update", args=[self.match.pk])

    def _post(self, payload):
        return self.client.post(
            self.url, data=json.dumps(payload), content_type="application/json"
        )

    def test_get_denied_for_outsider(self):
        self.client.force_login(self.outsider)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_get_returns_current_score(self):
        self.client.force_login(self.viewer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsNone(data["home_score"])
        self.assertEqual(data["status"], Match.Status.SCHEDULED)

    def test_viewer_cannot_update(self):
        self.client.force_login(self.viewer)
        response = self._post({"home_score": 1, "away_score": 0, "status": "live"})
        self.assertEqual(response.status_code, 403)

    def test_manager_can_start_live_and_update_score(self):
        self.client.force_login(self.manager)
        response = self._post({"home_score": 1, "away_score": 0, "status": "live"})
        self.assertEqual(response.status_code, 200)
        self.match.refresh_from_db()
        self.assertEqual(self.match.status, Match.Status.LIVE)
        self.assertEqual(self.match.home_score, 1)
        self.assertEqual(self.match.away_score, 0)

    def test_manager_can_finish_match(self):
        self.client.force_login(self.manager)
        response = self._post(
            {"home_score": 2, "away_score": 1, "status": "finished"}
        )
        self.assertEqual(response.status_code, 200)
        self.match.refresh_from_db()
        self.assertEqual(self.match.status, Match.Status.FINISHED)
        self.assertEqual(self.match.winner, self.team)

    def test_invalid_status_rejected(self):
        self.client.force_login(self.manager)
        response = self._post({"home_score": 1, "away_score": 0, "status": "bogus"})
        self.assertEqual(response.status_code, 400)

    def test_negative_score_rejected(self):
        self.client.force_login(self.manager)
        response = self._post({"home_score": -1, "away_score": 0, "status": "live"})
        self.assertEqual(response.status_code, 400)


class TournamentListViewTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model

        from accounts.models import OrganizationMembership

        User = get_user_model()
        self.staff = User.objects.create_user(
            username="staff", email="staff@example.com", password="pass12345"
        )
        self.staff.is_staff = True
        self.staff.save()
        self.user = User.objects.create_user(
            username="user", email="u@example.com", password="pass12345"
        )
        self.game = Game.objects.create(name="Valorant", slug="valorant")
        self.lol = Game.objects.create(name="League of Legends", slug="lol")
        self.t1 = Tournament.objects.create(
            name="Copa Nexus", game=self.game, participants_count=8, format=Tournament.Format.SWISS
        )
        self.t2 = Tournament.objects.create(
            name="Liga Invierno", game=self.lol, participants_count=16, format=Tournament.Format.ROUND_ROBIN
        )
        self.url = reverse("matches:tournament-list")

    def test_list_authenticated(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.t1, response.context["torneos"])

    def test_filter_by_game(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url, {"juego": self.game.pk})
        self.assertIn(self.t1, response.context["torneos"])
        self.assertNotIn(self.t2, response.context["torneos"])

    def test_staff_sees_create_button(self):
        self.client.force_login(self.staff)
        response = self.client.get(self.url)
        self.assertContains(response, "Nuevo Torneo")

    def test_non_staff_no_create_button(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertNotContains(response, "Nuevo Torneo")


class MatchFormTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model

        from accounts.models import OrganizationMembership

        User = get_user_model()
        self.manager = User.objects.create_user(
            username="manager", email="m@example.com", password="pass12345"
        )
        self.org = Organization.objects.create(
            name="Nova", slug="nova", abbreviation="NOVA"
        )
        self.game = Game.objects.create(name="Valorant", slug="valorant")
        self.team = Team.objects.create(
            organization=self.org, game=self.game, name="Nova Blue"
        )
        self.rival = Team.objects.create(
            organization=self.org, game=self.game, name="Nova Red"
        )
        OrganizationMembership.objects.create(
            user=self.manager,
            organization=self.org,
            role=OrganizationMembership.Role.ADMIN,
        )

    def test_form_excludes_result_and_external_opponent(self):
        from matches.forms import MatchForm

        form = MatchForm(user=self.manager)
        self.assertNotIn("away_name", form.fields)
        self.assertNotIn("home_score", form.fields)
        self.assertNotIn("away_score", form.fields)

    def test_form_requires_registered_away_team(self):
        from matches.forms import MatchForm

        form = MatchForm(
            data={
                "game": self.game.pk,
                "home_team": self.team.pk,
                "away_team": "",
                "kind": Match.Kind.OFFICIAL,
                "status": Match.Status.SCHEDULED,
                "scheduled_at": "2026-11-01T18:00",
                "best_of": 1,
            },
            user=self.manager,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("away_team", form.errors)

    def test_form_rejects_team_not_enrolled_in_tournament(self):
        from matches.forms import MatchForm

        tournament = Tournament.objects.create(
            name="Copa Nexus", game=self.game, participants_count=2
        )
        TournamentParticipant.objects.create(
            tournament=tournament, team=self.team
        )
        form = MatchForm(
            data={
                "game": self.game.pk,
                "home_team": self.team.pk,
                "away_team": self.rival.pk,
                "kind": Match.Kind.TOURNAMENT,
                "status": Match.Status.SCHEDULED,
                "scheduled_at": "2026-11-01T18:00",
                "tournament": tournament.pk,
                "best_of": 1,
            },
            user=self.manager,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("away_team", form.errors)

    def test_form_accepts_teams_enrolled_in_tournament(self):
        from matches.forms import MatchForm

        tournament = Tournament.objects.create(
            name="Copa Nexus", game=self.game, participants_count=2
        )
        TournamentParticipant.objects.create(
            tournament=tournament, team=self.team
        )
        TournamentParticipant.objects.create(
            tournament=tournament, team=self.rival
        )
        form = MatchForm(
            data={
                "game": self.game.pk,
                "home_team": self.team.pk,
                "away_team": self.rival.pk,
                "kind": Match.Kind.TOURNAMENT,
                "status": Match.Status.SCHEDULED,
                "scheduled_at": "2026-11-01T18:00",
                "tournament": tournament.pk,
                "best_of": 1,
            },
            user=self.manager,
        )
        self.assertTrue(form.is_valid(), form.errors)


class TournamentParticipantModelTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Nova", slug="nova", abbreviation="NOVA"
        )
        self.game = Game.objects.create(name="Valorant", slug="valorant")
        self.other_game = Game.objects.create(name="League of Legends", slug="lol")
        self.team = Team.objects.create(
            organization=self.org, game=self.game, name="Nova Blue"
        )
        self.tournament = Tournament.objects.create(
            name="Copa Nexus", game=self.game, participants_count=2
        )

    def test_unique_participant_per_tournament(self):
        TournamentParticipant.objects.create(
            tournament=self.tournament, team=self.team
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                TournamentParticipant.objects.create(
                    tournament=self.tournament, team=self.team
                )

    def test_team_must_belong_to_tournament_game(self):
        other_team = Team.objects.create(
            organization=self.org, game=self.other_game, name="Nova LoL"
        )
        participant = TournamentParticipant(
            tournament=self.tournament, team=other_team
        )
        with self.assertRaises(ValidationError) as ctx:
            participant.full_clean()
        self.assertIn("team", ctx.exception.message_dict)

    def test_mismatch_helper(self):
        TournamentParticipant.objects.create(
            tournament=self.tournament, team=self.team
        )
        self.assertEqual(self.tournament.participants_total, 1)
        self.assertTrue(self.tournament.has_participants_mismatch)


class TournamentFormParticipantTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Nova", slug="nova", abbreviation="NOVA"
        )
        self.game = Game.objects.create(name="Valorant", slug="valorant")
        self.other_game = Game.objects.create(name="League of Legends", slug="lol")
        self.teams = [
            Team.objects.create(organization=self.org, game=self.game, name=f"V{i}")
            for i in range(4)
        ]
        self.other_team = Team.objects.create(
            organization=self.org, game=self.other_game, name="L0"
        )

    def _data(self, **overrides):
        data = {
            "name": "Copa Nexus",
            "game": self.game.pk,
            "format": Tournament.Format.SINGLE_ELIMINATION,
            "participants_count": 4,
            "groups_count": 2,
            "participants": [team.pk for team in self.teams],
        }
        data.update(overrides)
        return data

    def test_form_saves_participants(self):
        from matches.forms import TournamentForm

        form = TournamentForm(data=self._data())
        self.assertTrue(form.is_valid(), form.errors)
        tournament = form.save()
        self.assertEqual(tournament.participants.count(), 4)

    def test_count_mismatch_does_not_block(self):
        from matches.forms import TournamentForm

        form = TournamentForm(
            data=self._data(participants=[self.teams[0].pk], participants_count=4)
        )
        self.assertTrue(form.is_valid(), form.errors)
        tournament = form.save()
        self.assertEqual(tournament.participants.count(), 1)
        self.assertTrue(tournament.has_participants_mismatch)

    def test_team_from_other_game_is_rejected(self):
        from matches.forms import TournamentForm

        form = TournamentForm(
            data=self._data(participants=[self.other_team.pk])
        )
        self.assertFalse(form.is_valid())
        self.assertIn("participants", form.errors)

    def test_groups_assigned_automatically(self):
        from matches.forms import TournamentForm

        form = TournamentForm(
            data=self._data(format=Tournament.Format.GROUPS_PLAYOFFS, groups_count=2)
        )
        self.assertTrue(form.is_valid(), form.errors)
        tournament = form.save()
        groups = set(
            tournament.participants.values_list("group_name", flat=True)
        )
        self.assertEqual(groups, {"A", "B"})


class TournamentParticipantsViewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_user(
            username="staff", email="s@example.com", password="pass12345"
        )
        self.staff.is_staff = True
        self.staff.save()
        self.user = User.objects.create_user(
            username="user", email="u@example.com", password="pass12345"
        )
        org = Organization.objects.create(
            name="Nova", slug="nova", abbreviation="NOVA"
        )
        self.game = Game.objects.create(name="Valorant", slug="valorant")
        self.team = Team.objects.create(
            organization=org, game=self.game, name="Nova Blue"
        )
        self.tournament = Tournament.objects.create(
            name="Copa Nexus", game=self.game, participants_count=2
        )
        self.url = reverse(
            "matches:tournament-participants", args=[self.tournament.pk]
        )

    def test_requires_staff(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_staff_can_view(self):
        self.client.force_login(self.staff)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_staff_can_add_participant(self):
        from matches.forms import TournamentParticipantFormSet

        self.client.force_login(self.staff)
        prefix = TournamentParticipantFormSet(
            instance=self.tournament
        ).prefix
        data = {
            f"{prefix}-TOTAL_FORMS": "1",
            f"{prefix}-INITIAL_FORMS": "0",
            f"{prefix}-MIN_NUM_FORMS": "0",
            f"{prefix}-MAX_NUM_FORMS": "1000",
            f"{prefix}-0-team": self.team.pk,
            f"{prefix}-0-group_name": "A",
            f"{prefix}-0-seed": "1",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.tournament.participants.count(), 1)


class BracketTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Nova", slug="nova", abbreviation="NOVA"
        )
        self.game = Game.objects.create(name="Valorant", slug="valorant")
        self.teams = [
            Team.objects.create(organization=self.org, game=self.game, name=f"V{i}")
            for i in range(6)
        ]
        self.tournament = Tournament.objects.create(
            name="Copa Nexus",
            game=self.game,
            format=Tournament.Format.SINGLE_ELIMINATION,
            participants_count=6,
        )

    def _add_participants(self, count, group_names=None):
        for index in range(count):
            TournamentParticipant.objects.create(
                tournament=self.tournament,
                team=self.teams[index],
                seed=index + 1,
                group_name=(group_names[index] if group_names else ""),
            )

    def test_single_elimination_sizes_and_byes(self):
        from matches.brackets import build_bracket

        self._add_participants(6)
        bracket = build_bracket(self.tournament)
        self.assertEqual(bracket["size"], 8)
        self.assertEqual(bracket["byes"], 2)
        first_round = bracket["brackets"][0]["rounds"][0]
        self.assertEqual(len(first_round["matches"]), 4)
        byes = [m for m in first_round["matches"] if m["bye"]]
        self.assertEqual(len(byes), 2)

    def test_bracket_without_enough_participants(self):
        from matches.brackets import build_bracket

        self._add_participants(1)
        self.assertIsNone(build_bracket(self.tournament))

    def test_groups_snake_distribution(self):
        from matches.brackets import build_groups

        self.tournament.format = Tournament.Format.GROUPS_PLAYOFFS
        self.tournament.groups_count = 2
        self.tournament.save()
        self._add_participants(4)
        groups = build_groups(self.tournament)
        self.assertEqual({group["name"] for group in groups}, {"A", "B"})
        self.assertEqual([group["count"] for group in groups], [2, 2])

    def test_standings_from_finished_match(self):
        from matches.brackets import build_standings

        self.tournament.format = Tournament.Format.ROUND_ROBIN
        self.tournament.save()
        self._add_participants(2)
        Match.objects.create(
            game=self.game,
            home_team=self.teams[0],
            away_team=self.teams[1],
            scheduled_at=timezone.now(),
            status=Match.Status.FINISHED,
            home_score=2,
            away_score=0,
            tournament=self.tournament,
        )
        rows = build_standings(self.tournament)["rows"]
        standings = {row["team"].pk: row for row in rows}
        self.assertEqual(standings[self.teams[0].pk]["points"], 3)
        self.assertEqual(standings[self.teams[1].pk]["points"], 0)

    def test_playoff_qualifiers_top_two(self):
        from matches.brackets import build_groups, playoff_qualifiers

        self.tournament.format = Tournament.Format.GROUPS_PLAYOFFS
        self.tournament.groups_count = 2
        self.tournament.save()
        self._add_participants(4)
        groups = build_groups(self.tournament)
        qualified = playoff_qualifiers(groups, per_group=2)
        self.assertEqual(len(qualified), 4)

    def test_double_elimination_has_two_brackets(self):
        from matches.brackets import build_bracket

        self.tournament.format = Tournament.Format.DOUBLE_ELIMINATION
        self.tournament.save()
        self._add_participants(4)
        bracket = build_bracket(self.tournament)
        self.assertEqual(len(bracket["brackets"]), 2)

    def test_first_round_exposes_seeds(self):
        from matches.brackets import build_bracket

        self._add_participants(6)
        first_round = build_bracket(self.tournament)["brackets"][0]["rounds"][0]
        seeded = [m for m in first_round["matches"] if not m["bye"]]
        self.assertTrue(seeded)
        for match in seeded:
            self.assertIsInstance(match["home_seed"], int)
            self.assertIsInstance(match["away_seed"], int)
        valid = {m["home_seed"] for m in seeded} | {m["away_seed"] for m in seeded}
        self.assertTrue(valid.issubset({1, 2, 3, 4, 5, 6}))

    def test_bracket_layout_geometry(self):
        from matches.brackets import build_bracket

        self._add_participants(6)
        bracket = build_bracket(self.tournament)["brackets"][0]
        layout = bracket["layout"]
        self.assertIsNotNone(layout)
        self.assertGreater(layout["width"], 0)
        self.assertGreater(layout["height"], 0)
        self.assertEqual(len(layout["titles"]), len(bracket["rounds"]))
        self.assertTrue(layout["paths"])
        for round_data in bracket["rounds"]:
            for match in round_data["matches"]:
                self.assertIn("x", match)
                self.assertIn("y", match)
        final = bracket["rounds"][-1]["matches"][0]
        first_centers = [
            m["y"] + layout["node_h"] / 2 for m in bracket["rounds"][0]["matches"]
        ]
        self.assertAlmostEqual(
            final["y"] + layout["node_h"] / 2,
            sum(first_centers) / len(first_centers),
            places=3,
        )

    def _two_team_tournament(self):
        tournament = Tournament.objects.create(
            name="Duelo",
            game=self.game,
            format=Tournament.Format.SINGLE_ELIMINATION,
            participants_count=2,
        )
        for index in range(2):
            TournamentParticipant.objects.create(
                tournament=tournament, team=self.teams[index], seed=index + 1
            )
        return tournament

    def test_finished_match_enriches_bracket(self):
        from matches.brackets import build_bracket

        tournament = self._two_team_tournament()
        match = Match.objects.create(
            game=self.game,
            home_team=self.teams[0],
            away_team=self.teams[1],
            scheduled_at=timezone.now(),
            status=Match.Status.FINISHED,
            home_score=2,
            away_score=1,
            tournament=tournament,
        )
        entry = build_bracket(tournament)["brackets"][0]["rounds"][0]["matches"][0]
        self.assertEqual(entry["match_pk"], match.pk)
        self.assertTrue(entry["has_score"])
        self.assertEqual(entry["home_score"], 2)
        self.assertEqual(entry["away_score"], 1)
        self.assertTrue(entry["is_finished"])
        self.assertEqual(entry["winner"], self.teams[0])

    def test_live_match_does_not_crown_winner(self):
        from matches.brackets import build_bracket

        tournament = self._two_team_tournament()
        Match.objects.create(
            game=self.game,
            home_team=self.teams[0],
            away_team=self.teams[1],
            scheduled_at=timezone.now(),
            status=Match.Status.LIVE,
            home_score=1,
            away_score=0,
            tournament=tournament,
        )
        entry = build_bracket(tournament)["brackets"][0]["rounds"][0]["matches"][0]
        self.assertTrue(entry["is_live"])
        self.assertIsNone(entry["winner"])


class TournamentDetailContextTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="user", email="u@example.com", password="pass12345"
        )
        org = Organization.objects.create(
            name="Nova", slug="nova", abbreviation="NOVA"
        )
        self.game = Game.objects.create(name="Valorant", slug="valorant")
        self.teams = [
            Team.objects.create(organization=org, game=self.game, name=f"V{i}")
            for i in range(4)
        ]

    def _tournament(self, tournament_format):
        tournament = Tournament.objects.create(
            name=f"Copa {tournament_format}",
            game=self.game,
            format=tournament_format,
            participants_count=4,
            groups_count=2,
        )
        for index, team in enumerate(self.teams, 1):
            TournamentParticipant.objects.create(
                tournament=tournament, team=team, seed=index
            )
        return tournament

    def _get_context(self, tournament):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("matches:tournament-detail", args=[tournament.pk])
        )
        self.assertEqual(response.status_code, 200)
        return response.context

    def test_single_elimination_has_bracket(self):
        context = self._get_context(
            self._tournament(Tournament.Format.SINGLE_ELIMINATION)
        )
        self.assertIsNotNone(context["bracket"])
        self.assertNotIn("groups", context)

    def test_groups_playoffs_has_groups_and_bracket(self):
        context = self._get_context(
            self._tournament(Tournament.Format.GROUPS_PLAYOFFS)
        )
        self.assertTrue(context["groups"])
        self.assertIsNotNone(context["bracket"])

    def test_round_robin_has_standings(self):
        context = self._get_context(self._tournament(Tournament.Format.ROUND_ROBIN))
        self.assertIsNotNone(context["standings"])
        self.assertNotIn("bracket", context)


class TournamentFormViewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_user(
            username="staff", email="s@example.com", password="pass12345"
        )
        self.staff.is_staff = True
        self.staff.save()
        org = Organization.objects.create(
            name="Nova", slug="nova", abbreviation="NOVA"
        )
        self.game = Game.objects.create(name="Valorant", slug="valorant")
        self.team = Team.objects.create(
            organization=org, game=self.game, name="Nova Blue"
        )
        self.tournament = Tournament.objects.create(
            name="Copa Nexus", game=self.game, participants_count=2
        )

    def test_create_form_renders_participant_grid(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("matches:tournament-create"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "data-team-grid")
        self.assertContains(response, 'data-game="%s"' % self.game.pk)

    def test_update_form_renders_with_participant_selected(self):
        TournamentParticipant.objects.create(
            tournament=self.tournament, team=self.team, seed=1
        )
        self.client.force_login(self.staff)
        response = self.client.get(
            reverse("matches:tournament-update", args=[self.tournament.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Copa Nexus")


class TournamentSerializerTests(TestCase):
    def test_serializer_includes_participants(self):
        from matches.serializers import TournamentSerializer

        org = Organization.objects.create(
            name="Nova", slug="nova", abbreviation="NOVA"
        )
        game = Game.objects.create(name="Valorant", slug="valorant")
        team = Team.objects.create(organization=org, game=game, name="Nova Blue")
        tournament = Tournament.objects.create(
            name="Copa Nexus", game=game, participants_count=2
        )
        TournamentParticipant.objects.create(
            tournament=tournament, team=team, seed=1, group_name="A"
        )
        data = TournamentSerializer(tournament).data
        self.assertEqual(data["participants_total"], 1)
        self.assertEqual(len(data["participants"]), 1)
        self.assertEqual(data["participants"][0]["team_name"], "Nova Blue")
        self.assertEqual(data["groups_count"], 2)


class MatchSerializerEnrollmentTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Nova", slug="nova", abbreviation="NOVA"
        )
        self.game = Game.objects.create(name="Valorant", slug="valorant")
        self.team_a = Team.objects.create(
            organization=self.org, game=self.game, name="Nova Blue"
        )
        self.team_b = Team.objects.create(
            organization=self.org, game=self.game, name="Nova Red"
        )
        self.tournament = Tournament.objects.create(
            name="Copa Nexus", game=self.game, participants_count=2
        )

    def _payload(self):
        return {
            "game": self.game.pk,
            "home_team": self.team_a.pk,
            "away_team": self.team_b.pk,
            "kind": Match.Kind.OFFICIAL,
            "status": Match.Status.SCHEDULED,
            "scheduled_at": "2026-11-01T18:00:00Z",
            "tournament": self.tournament.pk,
            "best_of": 1,
        }

    def test_serializer_rejects_unenrolled_teams(self):
        from matches.serializers import MatchSerializer

        serializer = MatchSerializer(data=self._payload())
        self.assertFalse(serializer.is_valid())
        self.assertIn("home_team", serializer.errors)
        self.assertIn("away_team", serializer.errors)

    def test_serializer_accepts_enrolled_teams(self):
        from matches.serializers import MatchSerializer

        TournamentParticipant.objects.create(
            tournament=self.tournament, team=self.team_a
        )
        TournamentParticipant.objects.create(
            tournament=self.tournament, team=self.team_b
        )
        serializer = MatchSerializer(data=self._payload())
        self.assertTrue(serializer.is_valid(), serializer.errors)
