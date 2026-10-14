from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

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

    def test_team_creation_with_image(self):
        from io import BytesIO
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.contrib.auth import get_user_model
        from accounts.models import OrganizationMembership

        User = get_user_model()
        user = User.objects.create_superuser(
            username="admin_test", email="admin_test@example.com", password="pass"
        )
        self.client.force_login(user)

        # Crear imagen en memoria
        img = Image.new("RGB", (100, 100), color="blue")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        uploaded = SimpleUploadedFile(
            "team_logo.png", buffer.getvalue(), content_type="image/png"
        )

        response = self.client.post(
            reverse("organizations:team-create"),
            {
                "organization": self.org.pk,
                "game": self.game.pk,
                "name": "Nova Red Prime",
                "slug": "nova-red-prime",
                "logo": uploaded,
                "status": "active",
                "description": "Equipo con imagen",
            },
        )
        self.assertEqual(response.status_code, 302)
        team = Team.objects.get(slug="nova-red-prime")
        self.assertTrue(bool(team.logo))
        self.assertEqual(team.image, team.logo)
        if team.logo:
            team.logo.delete(save=False)
