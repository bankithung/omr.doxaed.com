from django.urls import path

from .views import OrgPlanView, SubscribeView, WebhookView

urlpatterns = [
    path(
        "billing/organizations/<int:org_id>/subscribe/",
        SubscribeView.as_view(),
        name="billing-subscribe",
    ),
    path(
        "billing/organizations/<int:org_id>/plan/",
        OrgPlanView.as_view(),
        name="billing-org-plan",
    ),
    path(
        "billing/webhook/",
        WebhookView.as_view(),
        name="billing-webhook",
    ),
]
