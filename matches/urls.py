from django.urls import path

from matches import views

app_name = "matches"

urlpatterns = [
    path("partidos/", views.MatchListView.as_view(), name="match-list"),
    path("torneos/", views.TournamentListView.as_view(), name="tournament-list"),
    path(
        "torneos/nuevo/",
        views.TournamentCreateView.as_view(),
        name="tournament-create",
    ),
    path(
        "torneos/<int:pk>/",
        views.TournamentDetailView.as_view(),
        name="tournament-detail",
    ),
    path(
        "torneos/<int:pk>/editar/",
        views.TournamentUpdateView.as_view(),
        name="tournament-update",
    ),
    path(
        "torneos/<int:pk>/participantes/",
        views.TournamentParticipantsView.as_view(),
        name="tournament-participants",
    ),
    path(
        "torneos/<int:pk>/eliminar/",
        views.TournamentDeleteView.as_view(),
        name="tournament-delete",
    ),
    path("partidos/nuevo/", views.MatchCreateView.as_view(), name="match-create"),
    path("partidos/<int:pk>/", views.MatchDetailView.as_view(), name="match-detail"),
    path("partidos/<int:pk>/editar/", views.MatchUpdateView.as_view(), name="match-update"),
    path("partidos/<int:pk>/marcador/", views.MatchScoreView.as_view(), name="match-score-update"),
]