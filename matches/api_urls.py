from rest_framework.routers import DefaultRouter

from matches.api import (
    MatchMapViewSet,
    MatchViewSet,
    PlayerMatchStatViewSet,
    StatDefinitionViewSet,
    TeamMatchStatViewSet,
)

router = DefaultRouter()
router.register("matches", MatchViewSet, basename="match")
router.register("match-maps", MatchMapViewSet, basename="match-map")
router.register("stat-definitions", StatDefinitionViewSet, basename="stat-definition")
router.register("player-stats", PlayerMatchStatViewSet, basename="player-match-stat")
router.register("team-stats", TeamMatchStatViewSet, basename="team-match-stat")

urlpatterns = router.urls