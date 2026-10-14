"""Rutas de la API REST.

Cada aplicación expone sus endpoints mediante un ``DefaultRouter``. Todas las
rutas se montan bajo el prefijo ``/api/`` para mantenerlas separadas de las
páginas HTML, evitando duplicar nombres de ruta entre aplicaciones.
"""

from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path("auth-token/", obtain_auth_token, name="api_token_auth"),
    path("", include("accounts.api_urls")),
    path("", include("organizations.api_urls")),
    path("", include("players.api_urls")),
    path("", include("staff.api_urls")),
    path("", include("matches.api_urls")),
    path("", include("training.api_urls")),
]