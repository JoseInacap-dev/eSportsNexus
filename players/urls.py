from django.urls import path

from players import views

app_name = "players"

urlpatterns = [
    path("jugadores/", views.PlayerListView.as_view(), name="player-list"),
    path("jugadores/nuevo/", views.PlayerCreateView.as_view(), name="player-create"),
    path("jugadores/<int:pk>/", views.PlayerDetailView.as_view(), name="player-detail"),
    path("jugadores/<int:pk>/editar/", views.PlayerUpdateView.as_view(), name="player-update"),
    path(
        "jugadores/equipos/<int:team_pk>/asignar/",
        views.AssignmentCreateForTeamView.as_view(),
        name="team-assignment-create",
    ),
    path(
        "jugadores/<int:player_pk>/asignar/",
        views.AssignmentCreateForPlayerView.as_view(),
        name="player-assignment-create",
    ),
    path(
        "jugadores/asignaciones/<int:pk>/baja/",
        views.AssignmentFinishView.as_view(),
        name="assignment-finish",
    ),
]
