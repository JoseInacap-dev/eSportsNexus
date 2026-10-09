from rest_framework.routers import DefaultRouter

from organizations.api import (
    GameRoleViewSet,
    GameViewSet,
    OrganizationViewSet,
    TeamViewSet,
)

router = DefaultRouter()
router.register("organizations", OrganizationViewSet, basename="organization")
router.register("games", GameViewSet, basename="game")
router.register("game-roles", GameRoleViewSet, basename="game-role")
router.register("teams", TeamViewSet, basename="team")

urlpatterns = router.urls
