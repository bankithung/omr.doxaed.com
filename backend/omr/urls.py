from django.urls import path

from . import views

urlpatterns = [
    path("omr/generate/", views.GenerateView.as_view(), name="omr-generate"),
    path("omr/sheets/", views.OmrSheetListView.as_view(), name="omr-sheets"),
]
