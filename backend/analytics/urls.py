from django.urls import path

from analytics import views

urlpatterns = [
    path(
        "analytics/test/<int:test_id>/",
        views.test_analytics,
        name="analytics-test",
    ),
    path(
        "analytics/test/<int:test_id>/profile/",
        views.test_profile_view,
        name="analytics-test-profile",
    ),
    path(
        "analytics/test/<int:test_id>/student/<int:student_id>/",
        views.student_detail_view,
        name="analytics-student-detail",
    ),
    path(
        "analytics/test/<int:test_id>/improvement/",
        views.improvement_view,
        name="analytics-improvement",
    ),
    path(
        "analytics/test/<int:test_id>/export/",
        views.export_view,
        name="analytics-export",
    ),
]
