from rest_framework.routers import DefaultRouter

from accounts.api import OrganizationMembershipViewSet, UserViewSet

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
router.register("memberships", OrganizationMembershipViewSet, basename="membership")

urlpatterns = router.urls
