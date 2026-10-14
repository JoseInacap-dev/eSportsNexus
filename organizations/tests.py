import datetime
import shutil
import tempfile
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from accounts.models import OrganizationMembership, User
from organizations.forms import OrganizationForm
from organizations.models import Game, GameRole, Organization, Team
from players.models import Player, PlayerTeamAssignment


def _image_upload(name, image_format, content_type):
    buffer = BytesIO()
    Image.new("RGB", (12, 12), (120, 40, 200)).save(buffer, format=image_format)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=content_type)


def _png_upload(name="logo.png"):
    return _image_upload(name, "PNG", "image/png")


def _jpeg_upload(name="logo.jpg"):
    return _image_upload(name, "JPEG", "image/jpeg")


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
        self.org = Organization.objects.create(
            name="Nova Esports", slug="nova", abbreviation="NOVA"
        )
        self.game = Game.objects.create(name="Valorant", slug="valorant")

    def test_team_belongs_to_organization_and_game(self):
        team = Team.objects.create(
            organization=self.org, game=self.game, name="Nova Blue"
        )
        self.assertEqual(team.organization, self.org)
        self.assertEqual(team.game, self.game)
        self.assertEqual(self.org.teams.count(), 1)

    def test_team_inherits_organization_abbreviation(self):
        team = Team.objects.create(
            organization=self.org, game=self.game, name="Nova Blue"
        )
        self.assertEqual(team.abbreviation, "NOVA")
        self.org.abbreviation = "NVX"
        self.org.save()
        team.refresh_from_db()
        self.assertEqual(team.abbreviation, "NVX")

    def test_team_name_unique_within_org_and_game(self):
        Team.objects.create(
            organization=self.org, game=self.game, name="Nova Blue"
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Team.objects.create(
                    organization=self.org,
                    game=self.game,
                    name="Nova Blue",
                )


class OrganizationFormTests(TestCase):
    def test_form_sets_slug_from_name(self):
        form = OrganizationForm(
            data={"name": "Furia Gaming", "abbreviation": "FUR", "is_active": True}
        )
        self.assertTrue(form.is_valid(), form.errors)
        organization = form.save()
        self.assertEqual(organization.slug, "furia-gaming")

    def test_slug_is_unique(self):
        Organization.objects.create(name="Nova", slug="nova", abbreviation="NOVA")
        form = OrganizationForm(
            data={"name": "Nova!", "abbreviation": "NOVA2", "is_active": True}
        )
        self.assertTrue(form.is_valid(), form.errors)
        organization = form.save()
        self.assertEqual(organization.slug, "nova-2")


class OrganizationManagementTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="owner", email="owner@example.com", password="pass12345"
        )
        self.other = User.objects.create_user(
            username="other", email="other@example.com", password="pass12345"
        )
        self.superuser = User.objects.create_superuser(
            username="root", email="root@example.com", password="pass12345"
        )
        self.org = Organization.objects.create(
            name="Nova Esports", slug="nova", abbreviation="NOVA"
        )
        OrganizationMembership.objects.create(
            user=self.user,
            organization=self.org,
            role=OrganizationMembership.Role.OWNER,
        )

    def test_create_organization_assigns_owner(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("organizations:organization-create"),
            {
                "name": "Furia Gaming",
                "abbreviation": "FUR",
                "country": "Argentina",
                "is_active": True,
            },
        )
        organization = Organization.objects.get(name="Furia Gaming")
        self.assertRedirects(
            response,
            reverse(
                "organizations:organization-detail", args=[organization.pk]
            ),
        )
        self.assertTrue(
            OrganizationMembership.objects.filter(
                user=self.user,
                organization=organization,
                role=OrganizationMembership.Role.OWNER,
                is_active=True,
            ).exists()
        )

    def test_list_scoped_to_membership(self):
        Organization.objects.create(
            name="Rival Esports", slug="rival", abbreviation="RIVAL"
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse("organizations:organization-list"))
        self.assertContains(response, "Nova Esports")
        self.assertNotContains(response, "Rival Esports")

    def test_superuser_sees_all_organizations(self):
        Organization.objects.create(
            name="Rival Esports", slug="rival", abbreviation="RIVAL"
        )
        self.client.force_login(self.superuser)
        response = self.client.get(reverse("organizations:organization-list"))
        self.assertContains(response, "Nova Esports")
        self.assertContains(response, "Rival Esports")

    def test_non_member_cannot_view_detail(self):
        self.client.force_login(self.other)
        response = self.client.get(
            reverse("organizations:organization-detail", args=[self.org.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_viewer_cannot_edit(self):
        OrganizationMembership.objects.create(
            user=self.other,
            organization=self.org,
            role=OrganizationMembership.Role.VIEWER,
        )
        self.client.force_login(self.other)
        response = self.client.get(
            reverse("organizations:organization-update", args=[self.org.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_owner_can_edit(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("organizations:organization-update", args=[self.org.pk]),
            {
                "name": "Nova Esports Renovada",
                "abbreviation": "NOVA",
                "country": "España",
                "is_active": True,
            },
        )
        self.assertRedirects(
            response,
            reverse("organizations:organization-detail", args=[self.org.pk]),
        )
        self.org.refresh_from_db()
        self.assertEqual(self.org.name, "Nova Esports Renovada")


class OrganizationLogoTests(TestCase):
    def setUp(self):
        self.media_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media_dir, ignore_errors=True)
        override = override_settings(MEDIA_ROOT=self.media_dir)
        override.enable()
        self.addCleanup(override.disable)
        self.user = User.objects.create_user(
            username="logoowner", email="logo@example.com", password="pass12345"
        )

    def test_upload_png_logo_via_form(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("organizations:organization-create"),
            {
                "name": "Furia Gaming",
                "abbreviation": "FUR",
                "country": "Argentina",
                "is_active": True,
                "logo": _png_upload(),
            },
        )
        organization = Organization.objects.get(name="Furia Gaming")
        self.assertRedirects(
            response,
            reverse(
                "organizations:organization-detail", args=[organization.pk]
            ),
        )
        self.assertTrue(organization.logo)
        self.assertTrue(organization.logo.name.endswith(".png"))
        self.assertEqual(organization.logo_display, organization.logo.url)

    def test_rejects_non_png_logo(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("organizations:organization-create"),
            {
                "name": "JPG Org",
                "abbreviation": "JPGORG",
                "is_active": True,
                "logo": _jpeg_upload(),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Organization.objects.filter(name="JPG Org").exists())

    def test_logo_display_falls_back_to_url(self):
        organization = Organization.objects.create(
            name="URL Org",
            slug="url-org",
            abbreviation="URLORG",
            logo_url="https://example.com/logo.png",
        )
        self.assertEqual(
            organization.logo_display, "https://example.com/logo.png"
        )

    def test_logo_is_optional(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("organizations:organization-create"),
            {
                "name": "Sin Logo",
                "abbreviation": "SINLOGO",
                "is_active": True,
            },
        )
        self.assertEqual(response.status_code, 302)
        organization = Organization.objects.get(name="Sin Logo")
        self.assertFalse(organization.logo)
        self.assertEqual(organization.logo_display, "")

    def test_form_renders_logo_inputs(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("organizations:organization-create"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'enctype="multipart/form-data"')
        self.assertContains(response, 'type="file"')
        self.assertContains(response, 'name="logo_url"')


class TeamCoachTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="owner", email="owner@example.com", password="pass12345"
        )
        self.org = Organization.objects.create(
            name="Nova Esports", slug="nova", abbreviation="NOVA"
        )
        OrganizationMembership.objects.create(
            user=self.user,
            organization=self.org,
            role=OrganizationMembership.Role.OWNER,
        )
        self.game = Game.objects.create(name="Valorant", slug="valorant")
        self.coach_role = GameRole.objects.create(game=self.game, name="Coach")
        self.player_role = GameRole.objects.create(game=self.game, name="Duelist")
        self.team = Team.objects.create(
            organization=self.org, game=self.game, name="Nova Blue"
        )

    def _assign(self, nickname, role, **kwargs):
        player = Player.objects.create(first_name=nickname, nickname=nickname)
        assignment = PlayerTeamAssignment.objects.create(
            player=player,
            team=self.team,
            competitive_role=role,
            joined_at=datetime.date(2026, 1, 1),
            **kwargs,
        )
        return player, assignment

    def test_coach_assignments_property(self):
        coach, _ = self._assign("coachito", self.coach_role)
        self._assign("faker", self.player_role)
        self.assertEqual(
            [a.player for a in self.team.coach_assignments], [coach]
        )

    def test_players_count_excludes_coaches(self):
        self._assign("coachito", self.coach_role)
        self._assign("faker", self.player_role)
        self.assertEqual(self.team.players_count, 1)

    def test_players_count_includes_assignment_without_role(self):
        self._assign("libre", None)
        self.assertEqual(self.team.players_count, 1)

    def test_team_detail_separates_coach_from_roster(self):
        self._assign("coachito", self.coach_role)
        self._assign("faker", self.player_role)
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("organizations:team-detail", args=[self.team.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [a.player.nickname for a in response.context["coaches"]],
            ["coachito"],
        )
        self.assertEqual(
            [a.player.nickname for a in response.context["jugadores"]],
            ["faker"],
        )

    def test_team_list_shows_coach_section(self):
        self._assign("coachito", self.coach_role)
        self.client.force_login(self.user)
        response = self.client.get(reverse("organizations:team-list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "coachito")
