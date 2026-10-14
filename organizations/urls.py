from django.urls import path

from organizations import views

app_name = "organizations"

urlpatterns = [
    path("equipos/", views.TeamListView.as_view(), name="team-list"),
    path("equipos/nuevo/", views.TeamCreateView.as_view(), name="team-create"),
    path("equipos/<int:pk>/", views.TeamDetailView.as_view(), name="team-detail"),
    path("equipos/<int:pk>/editar/", views.TeamUpdateView.as_view(), name="team-update"),
    path("equipos/<int:pk>/eliminar/", views.TeamDeleteView.as_view(), name="team-delete"),
    path(
        "organizaciones/",
        views.OrganizationListView.as_view(),
        name="organization-list",
    ),
    path(
        "organizaciones/nueva/",
        views.OrganizationCreateView.as_view(),
        name="organization-create",
    ),
    path(
        "organizaciones/<int:pk>/",
        views.OrganizationDetailView.as_view(),
        name="organization-detail",
    ),
    path(
        "organizaciones/<int:pk>/editar/",
        views.OrganizationUpdateView.as_view(),
        name="organization-update",
    ),
]
