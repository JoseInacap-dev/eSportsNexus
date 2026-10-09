from rest_framework.routers import DefaultRouter

from staff.api import StaffMemberViewSet, TeamStaffAssignmentViewSet

router = DefaultRouter()
router.register("staff-members", StaffMemberViewSet, basename="staff-member")
router.register("staff-assignments", TeamStaffAssignmentViewSet, basename="staff-assignment")

urlpatterns = router.urls