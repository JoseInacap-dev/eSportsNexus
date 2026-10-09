from django.urls import path

from training import views

app_name = "training"

urlpatterns = [
    path("entrenamientos/", views.TrainingSessionListView.as_view(), name="session-list"),
    path("entrenamientos/nuevo/", views.TrainingSessionCreateView.as_view(), name="session-create"),
    path("entrenamientos/<int:pk>/editar/", views.TrainingSessionUpdateView.as_view(), name="session-update"),
]