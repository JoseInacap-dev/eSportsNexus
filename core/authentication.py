"""Autenticación personalizada para pruebas directas en Postman y navegadores."""

from django.contrib.auth import get_user_model
from rest_framework.authentication import BaseAuthentication
from rest_framework.authtoken.models import Token


class QueryParamAuthentication(BaseAuthentication):
    """Permite autenticar pasando ?auth=admin o ?token=<token> directamente en la URL en Postman o navegador."""

    def authenticate(self, request):
        auth_param = request.query_params.get("auth") or request.query_params.get("token")
        if not auth_param:
            return None

        User = get_user_model()
        if auth_param in ("admin", "admin:Nexus2026"):
            user = User.objects.filter(is_superuser=True).first()
            if user:
                return (user, None)

        try:
            token = Token.objects.select_related("user").filter(key=auth_param).first()
            if token and token.user.is_active:
                return (token.user, token)
        except Exception:
            pass

        return None
