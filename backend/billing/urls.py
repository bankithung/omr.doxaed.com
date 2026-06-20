from django.urls import path

from .views import OrgPlanView, PlanListView, SubscribeView, WebhookView

urlpatterns = [
    path(
        "billing/plans/",
        PlanListView.as_view(),
        name="billing-plans-list",
    ),
    path(
        "billing/organizations/<uuid:org_id>/subscribe/",
        SubscribeView.as_view(),
        name="billing-subscribe",
    ),
    path(
        "billing/organizations/<uuid:org_id>/plan/",
        OrgPlanView.as_view(),
        name="billing-org-plan",
    ),
    path(
        "billing/webhook/",
        WebhookView.as_view(),
        name="billing-webhook",
    ),
]
