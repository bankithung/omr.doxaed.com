from django.urls import path

from analytics import views

urlpatterns = [
    path(
        "analytics/test/<int:test_id>/",
        views.test_analytics,
        name="analytics-test",
    ),
]
