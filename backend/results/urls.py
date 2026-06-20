from django.urls import path

from results import views

urlpatterns = [
    path("results/", views.StudentResultListView.as_view(), name="results-list"),
    path("review/", views.ReviewItemListView.as_view(), name="review-list"),
    path("review/<uuid:pk>/resolve/", views.ResolveReviewItemView.as_view(), name="review-resolve"),
]
