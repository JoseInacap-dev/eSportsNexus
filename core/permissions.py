"""Permisos de la plataforma.

La autorización se basa en :class:`accounts.models.OrganizationMembership`:
un usuario puede operar sobre una organización (y sus equipos) en función de
su rol. Estos helpers se usan tanto en las vistas HTML como en la API REST.
"""

from rest_framework import permissions

from accounts.models import OrganizationMembership

# Roles con capacidad de escritura (gestión).
MANAGEMENT_ROLES = frozenset(
    {
        OrganizationMembership.Role.OWNER,
        OrganizationMembership.Role.ADMIN,
        OrganizationMembership.Role.COACH,
        OrganizationMembership.Role.STAFF,
    }
)

# Cualquier rol activo puede visualizar.
READ_ROLES = frozenset(role for role, _label in OrganizationMembership.Role.choices)


def user_has_organization_role(user, organization, roles):
    if not user or not user.is_authenticated or organization is None:
        return False
    if user.is_superuser:
        return True
    return OrganizationMembership.objects.filter(
        user=user,
        organization=organization,
        is_active=True,
        role__in=roles,
    ).exists()


def user_can_manage_organization(user, organization):
    return user_has_organization_role(user, organization, MANAGEMENT_ROLES)


def user_can_view_organization(user, organization):
    return user_has_organization_role(user, organization, READ_ROLES)


def user_manages_any_organization(user):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return OrganizationMembership.objects.filter(
        user=user, is_active=True, role__in=MANAGEMENT_ROLES
    ).exists()


def organization_of(obj):
    """Obtiene la organización asociada a un objeto de dominio.

    Recorre los atributos habituales (``organization``, ``team``,
    ``home_team``) para soportar equipos, asignaciones, partidos, etc.
    """
    if obj is None:
        return None
    organization = getattr(obj, "organization", None)
    if organization is not None:
        return organization
    team = getattr(obj, "team", None)
    if team is not None:
        return team.organization
    home_team = getattr(obj, "home_team", None)
    if home_team is not None:
        return home_team.organization
    return None


class IsOrganizationManager(permissions.BasePermission):
    """Permite escritura solo a gestores de la organización del objeto."""

    message = "No tienes permisos para gestionar esta organización."

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return user_can_view_organization(request.user, organization_of(obj))
        return user_can_manage_organization(request.user, organization_of(obj))
