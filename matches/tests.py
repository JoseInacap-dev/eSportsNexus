import datetime
import json

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
