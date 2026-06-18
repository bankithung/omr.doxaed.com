"""
results.public_urls — no-auth public portal URL patterns.

Wired into config/urls.py as:
    path("api/v1/public/", include("results.public_urls"))
"""
from django.urls import path

from results import public_views

urlpatterns = [
    path("r/<str:slug>/", public_views.portal_meta, name="public-portal-meta"),
    path("r/<str:slug>/lookup/", public_views.portal_lookup, name="public-portal-lookup"),
    path("r/<str:slug>/leaderboard/", public_views.portal_leaderboard, name="public-portal-leaderboard"),
]
