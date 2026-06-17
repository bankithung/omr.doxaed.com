from django.urls import path

from .views import SubscribeView, WebhookView

urlpatterns = [
    path(
        "billing/organizations/<int:org_id>/subscribe/",
        SubscribeView.as_view(),
        name="billing-subscribe",
    ),
    path(
        "billing/webhook/",
        WebhookView.as_view(),
        name="billing-webhook",
    ),
]
