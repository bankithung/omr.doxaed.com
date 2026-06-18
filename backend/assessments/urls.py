from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("classes", views.ClassGroupViewSet, basename="class")
router.register("tests", views.TestViewSet, basename="test")
router.register("questions", views.QuestionViewSet, basename="question")
router.register("sections", views.SectionViewSet, basename="section")

urlpatterns = router.urls
