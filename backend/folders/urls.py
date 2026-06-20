from django.urls import path
from rest_framework.routers import DefaultRouter

from folders import views

router = DefaultRouter()
router.register("folders", views.FolderViewSet, basename="folder")
router.register("subjects", views.SubjectViewSet, basename="subject")

_share_list = views.FolderShareViewSet.as_view({"get": "list", "post": "create"})
_share_detail = views.FolderShareViewSet.as_view({"delete": "destroy"})

urlpatterns = router.urls + [
    path(
        "folders/<uuid:folder_pk>/shares/",
        _share_list,
        name="folder-shares-list",
    ),
    path(
        "folders/<uuid:folder_pk>/shares/<uuid:pk>/",
        _share_detail,
        name="folder-shares-detail",
    ),
]
