import datetime

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
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
        self.org = Organization.objects.create(name="Nova", slug="nova")
        self.game = Game.objects.create(name="Valorant", slug="valorant")
        self.team_a = Team.objects.create(
            organization=self.org, game=self.game, name="Nova Blue", slug="nova-blue"
        )
        self.team_b = Team.objects.create(
            organization=self.org, game=self.game, name="Nova Red", slug="nova-red"
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

    def test_external_opponent_required_when_no_away_team(self):
        match = self._match(away_team=None, away_name="")
        with self.assertRaises(ValidationError):
            match.full_clean()

    def test_external_opponent_is_valid(self):
        match = self._match(away_team=None, away_name="Furia")
        match.full_clean()
        match.save()
        self.assertIn("Furia", str(match))

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
            organization=self.org, game=other_game, name="Nova LoL", slug="nova-lol"
        )
        match = self._match(home_team=other_team)
        with self.assertRaises(ValidationError) as ctx:
            match.full_clean()
        self.assertIn("home_team", ctx.exception.message_dict)


class MatchMapTests(TestCase):
    def setUp(self):
        org = Organization.objects.create(name="Nova", slug="nova")
        game = Game.objects.create(name="Valorant", slug="valorant")
        self.team = Team.objects.create(
            organization=org, game=game, name="Nova Blue", slug="nova-blue"
        )
        self.match = Match.objects.create(
            game=game,
            home_team=self.team,
            away_name="Furia",
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
        org = Organization.objects.create(name="Nova", slug="nova")
        game = Game.objects.create(name="Valorant", slug="valorant")
        self.team = Team.objects.create(
            organization=org, game=game, name="Nova Blue", slug="nova-blue"
        )
        self.match = Match.objects.create(
            game=game,
            home_team=self.team,
            away_name="Furia",
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
