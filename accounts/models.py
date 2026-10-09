from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """Usuario de la plataforma.

    Extiende ``AbstractUser`` para poder añadir campos de perfil sin duplicar
    los datos de autenticación que gestiona Django (password, last_login, etc.).
    Se define desde el inicio como modelo de usuario del proyecto para evitar
    migraciones destructivas posteriores.
    """

    email = models.EmailField(_("correo electrónico"), unique=True)
    display_name = models.CharField(_("nombre visible"), max_length=150, blank=True)
    phone = models.CharField(_("teléfono"), max_length=32, blank=True)
    created_at = models.DateTimeField(_("creado"), auto_now_add=True)
    updated_at = models.DateTimeField(_("actualizado"), auto_now=True)

    class Meta:
        verbose_name = _("usuario")
        verbose_name_plural = _("usuarios")
        ordering = ["username"]

    def __str__(self):
        return self.display_name or self.get_full_name() or self.username


class OrganizationMembership(models.Model):
    """Vínculo entre un usuario y una organización, con su rol de acceso.

    Es la base del control de permisos: determina sobre qué organización (y,
    por extensión, sobre qué equipos) puede operar cada usuario.
    """

    class Role(models.TextChoices):
        OWNER = "owner", _("Propietario")
        ADMIN = "admin", _("Administrador")
        COACH = "coach", _("Entrenador")
        STAFF = "staff", _("Staff")
        VIEWER = "viewer", _("Consulta")

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="organization_memberships",
        verbose_name=_("usuario"),
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="memberships",
        verbose_name=_("organización"),
    )
    role = models.CharField(
        _("rol"), max_length=16, choices=Role.choices, default=Role.VIEWER
    )
    is_active = models.BooleanField(_("activo"), default=True)
    created_at = models.DateTimeField(_("creado"), auto_now_add=True)
    updated_at = models.DateTimeField(_("actualizado"), auto_now=True)

    class Meta:
        verbose_name = _("membresía de organización")
        verbose_name_plural = _("membresías de organización")
        ordering = ["organization", "user"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "organization"],
                name="unique_user_organization_membership",
            )
        ]
        indexes = [
            models.Index(fields=["organization", "role"]),
        ]

    def __str__(self):
        return f"{self.user} · {self.organization} ({self.get_role_display()})"
