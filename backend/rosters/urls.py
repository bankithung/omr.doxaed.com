from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("rosters", views.RosterViewSet, basename="roster")
router.register("students", views.StudentViewSet, basename="student")

urlpatterns = router.urls
