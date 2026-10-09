from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from accounts.models import OrganizationMembership, User
from organizations.models import Organization


class UserModelTests(TestCase):
    def test_create_user_and_str(self):
        user = User.objects.create_user(
            username="ana", email="ana@example.com", password="s3cret-pass"
        )
        self.assertEqual(str(user), "ana")
        self.assertTrue(user.check_password("s3cret-pass"))

    def test_email_is_unique(self):
        User.objects.create_user(username="a", email="dup@example.com", password="x")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(
                    username="b", email="dup@example.com", password="x"
                )


class OrganizationMembershipTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Nova Esports", slug="nova")
        self.user = User.objects.create_user(
            username="u1", email="u1@example.com", password="x"
        )

    def test_membership_has_role(self):
        membership = OrganizationMembership.objects.create(
            user=self.user,
            organization=self.org,
            role=OrganizationMembership.Role.ADMIN,
        )
        self.assertIn("Administrador", str(membership))

    def test_user_cannot_have_duplicate_membership(self):
        OrganizationMembership.objects.create(user=self.user, organization=self.org)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                OrganizationMembership.objects.create(
                    user=self.user, organization=self.org
                )


class AuthFlowTests(TestCase):
    def test_signup_creates_user(self):
        response = self.client.get(reverse("accounts:signup"))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "username": "jugador1",
                "email": "jugador1@example.com",
                "display_name": "Jugador Uno",
                "password1": "S3cr3t-pass-2026",
                "password2": "S3cr3t-pass-2026",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username="jugador1").exists())

    def test_login_and_logout(self):
        User.objects.create_user(
            username="jefa", email="jefa@example.com", password="S3cr3t-pass-2026"
        )
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "jefa", "password": "S3cr3t-pass-2026"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue("_auth_user_id" in self.client.session)

        # Django 5+ exige POST para cerrar sesión.
        response = self.client.post(reverse("accounts:logout"))
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)
