from django.urls import path

from matches import views

app_name = "matches"

urlpatterns = [
    path("partidos/", views.MatchListView.as_view(), name="match-list"),
    path("partidos/nuevo/", views.MatchCreateView.as_view(), name="match-create"),
    path("partidos/<int:pk>/", views.MatchDetailView.as_view(), name="match-detail"),
    path("partidos/<int:pk>/editar/", views.MatchUpdateView.as_view(), name="match-update"),
]