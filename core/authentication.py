"""Autenticación personalizada para pruebas directas en Postman y navegadores."""

from rest_framework.authentication import BaseAuthentication
from rest_framework.authtoken.models import Token


class QueryParamAuthentication(BaseAuthentication):
    """Permite autenticar pasando ?token=<token> directamente en la URL en Postman o navegador."""

    def authenticate(self, request):
        auth_param = request.query_params.get("auth") or request.query_params.get("token")
        if not auth_param:
            return None

        try:
            token = Token.objects.select_related("user").filter(key=auth_param).first()
            if token and token.user.is_active:
                return (token.user, token)
        except Exception:
            pass

        return None
