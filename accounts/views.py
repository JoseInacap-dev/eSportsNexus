from django.urls import reverse_lazy
from django.views.generic import CreateView

from accounts.forms import UserRegistrationForm


class SignUpView(CreateView):
    """Registro de usuarios normales con perfil estándar.

    Crea un usuario regular sin permisos administrativos ni roles de gestión.
    Los permisos y membresías deben configurarse desde el panel de Administración
    por un usuario administrador.
    """

    form_class = UserRegistrationForm
    template_name = "registration/signup.html"
    success_url = reverse_lazy("accounts:login")
