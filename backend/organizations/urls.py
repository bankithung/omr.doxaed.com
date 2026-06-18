from django.urls import path

from .views import (
    AcceptInviteView,
    AuditLogView,
    InviteView,
    MemberDetailView,
    MemberListView,
    OrgBrandingView,
    OrganizationListCreateView,
)

urlpatterns = [
    # Organization CRUD
    path("organizations/", OrganizationListCreateView.as_view(), name="org-list-create"),

    # Invitation
    path("organizations/<int:org_id>/invite/", InviteView.as_view(), name="org-invite"),
    path("invitations/accept/", AcceptInviteView.as_view(), name="invitation-accept"),

    # Member management
    path("organizations/<int:org_id>/members/", MemberListView.as_view(), name="org-members"),
    path(
        "organizations/<int:org_id>/members/<int:user_id>/",
        MemberDetailView.as_view(),
        name="org-member-detail",
    ),

    # Audit log
    path("organizations/<int:org_id>/audit/", AuditLogView.as_view(), name="org-audit"),

    # Branding (Phase 3c)
    path("organizations/<int:org_id>/branding/", OrgBrandingView.as_view(), name="org-branding"),
]
