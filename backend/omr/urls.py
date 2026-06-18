from django.urls import path

from . import views

urlpatterns = [
    path("omr/generate/", views.GenerateView.as_view(), name="omr-generate"),
    path("omr/sheets/", views.OmrSheetListView.as_view(), name="omr-sheets"),
    path(
        "omr/sheets/<int:pk>/question-paper/",
        views.OmrSheetQuestionPaperView.as_view(),
        name="omr-sheet-question-paper",
    ),
    path("omr/scan/", views.ScanUploadView.as_view(), name="omr-scan-upload"),
    path("omr/scan-batches/<int:pk>/", views.ScanBatchDetailView.as_view(), name="omr-scan-batch-detail"),
]
