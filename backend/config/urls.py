from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from common.views import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/health/", health),
    path("api/v1/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/v1/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/v1/auth/", include("accounts.urls")),
    path("api/v1/", include("assessments.urls")),
    path("api/v1/", include("rosters.urls")),
    path("api/v1/", include("omr.urls")),
    path("api/v1/", include("results.urls")),
    path("api/v1/", include("analytics.urls")),
    path("api/v1/", include("organizations.urls")),
    path("api/v1/", include("billing.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
