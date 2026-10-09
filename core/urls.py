from django.urls import path

from core import views

app_name = "core"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("estadisticas/", views.EstadisticasView.as_view(), name="estadisticas"),
    path("configuracion/", views.AjustesView.as_view(), name="ajustes"),
]
