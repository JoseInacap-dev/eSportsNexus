from rest_framework.routers import DefaultRouter

from players.api import PlayerTeamAssignmentViewSet, PlayerViewSet

router = DefaultRouter()
router.register("players", PlayerViewSet, basename="player")
router.register("player-assignments", PlayerTeamAssignmentViewSet, basename="player-assignment")

urlpatterns = router.urls