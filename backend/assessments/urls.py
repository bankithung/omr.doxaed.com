from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("classes", views.ClassGroupViewSet, basename="class")
router.register("tests", views.TestViewSet, basename="test")

urlpatterns = router.urls
