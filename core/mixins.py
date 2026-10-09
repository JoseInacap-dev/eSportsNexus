from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

from core.permissions import user_can_manage_organization, user_can_view_organization


class OrganizationAccessMixin(LoginRequiredMixin):
    """Restringe el acceso a la organización asociada a la vista.

    Las subclases deben implementar :meth:`get_organization`. Con
    ``require_manage = True`` se exige un rol de gestión.
    """

    require_manage = False

    def get_organization(self):
        raise NotImplementedError(
            "Las vistas con OrganizationAccessMixin deben definir get_organization()."
        )

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            organization = self.get_organization()
            if organization is not None:
                checker = (
                    user_can_manage_organization
                    if self.require_manage
                    else user_can_view_organization
                )
                if not checker(request.user, organization):
                    raise PermissionDenied(
                        "No tienes acceso a esta organización."
                    )
        return super().dispatch(request, *args, **kwargs)
