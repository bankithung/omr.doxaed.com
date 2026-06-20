from django.urls import path

from analytics import views

urlpatterns = [
    path(
        "analytics/test/<uuid:test_id>/",
        views.test_analytics,
        name="analytics-test",
    ),
    path(
        "analytics/test/<uuid:test_id>/profile/",
        views.test_profile_view,
        name="analytics-test-profile",
    ),
    path(
        "analytics/test/<uuid:test_id>/student/<uuid:student_id>/",
        views.student_detail_view,
        name="analytics-student-detail",
    ),
    path(
        "analytics/test/<uuid:test_id>/student/<uuid:student_id>/report-card/",
        views.student_report_card_view,
        name="analytics-student-report-card",
    ),
    path(
        "analytics/test/<uuid:test_id>/report-cards/",
        views.bulk_report_cards_view,
        name="analytics-bulk-report-cards",
    ),
    path(
        "analytics/test/<uuid:test_id>/improvement/",
        views.improvement_view,
        name="analytics-improvement",
    ),
    path(
        "analytics/test/<uuid:test_id>/export/",
        views.export_view,
        name="analytics-export",
    ),
    path(
        "analytics/test/<uuid:test_id>/publish/",
        views.test_publish_view,
        name="analytics-test-publish",
    ),
]
