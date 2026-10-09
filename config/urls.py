"""URLConf principal.

Se separan claramente:
- Las rutas de páginas HTML (renderizadas por Django, agrupadas por aplicación).
- Las rutas de la API REST, bajo el prefijo ``/api/``.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # Páginas visuales (HTML)
    path("", include("core.urls")),
    path("cuenta/", include("accounts.urls")),
    path("", include("organizations.urls")),
    path("", include("players.urls")),
    path("", include("matches.urls")),
    path("", include("training.urls")),
    # API REST
    path("api/", include("config.api_urls")),
]