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
    path(
        "omr/sheets/<int:pk>/regrade/",
        views.OmrSheetRegradeView.as_view(),
        name="omr-sheet-regrade",
    ),
    path(
        "omr/tests/<int:pk>/question-papers/",
        views.OmrTestQuestionPapersBatchView.as_view(),
        name="omr-test-question-papers-batch",
    ),
    path("omr/scan/", views.ScanUploadView.as_view(), name="omr-scan-upload"),
    path("omr/scan-batches/<int:pk>/", views.ScanBatchDetailView.as_view(), name="omr-scan-batch-detail"),
    path(
        "omr/scan-batches/<int:pk>/sheets/",
        views.ScanBatchSheetsView.as_view(),
        name="omr-scan-batch-sheets",
    ),
    path(
        "omr/scan-jobs/<int:pk>/warped/",
        views.ScanJobWarpedView.as_view(),
        name="omr-scan-job-warped",
    ),
]
