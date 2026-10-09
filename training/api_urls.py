from rest_framework.routers import DefaultRouter

from training.api import TrainingAttendanceViewSet, TrainingSessionViewSet

router = DefaultRouter()
router.register("training-sessions", TrainingSessionViewSet, basename="training-session")
router.register("training-attendance", TrainingAttendanceViewSet, basename="training-attendance")

urlpatterns = router.urls