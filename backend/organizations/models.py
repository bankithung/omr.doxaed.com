import uuid

from django.conf import settings
from django.db import models

from common.logo_validators import validate_logo_image


class Organization(models.Model):
    """Phase 0 skeleton. Membership, invitations, roles, audit log arrive in Phase 6.
    Exists now because the owner-scope foundation references this table."""

    PERSONAL = "personal"
    SCHOOL = "school"
    COLLEGE = "college"
    UNIVERSITY = "university"
    COACHING = "coaching"
    OTHER = "other"
    TYPE_CHOICES = [
        (PERSONAL, "Personal"),
        (SCHOOL, "School"),
        (COLLEGE, "College"),
        (UNIVERSITY, "University"),
        (COACHING, "Coaching"),
        (OTHER, "Other"),
    ]

    name = models.CharField(max_length=255)
    # Org type seeds the default level labels for the nested-group tree
    # (school → Class/Section, university → Department/Program/Batch, …).
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=OTHER)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_organizations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # --- Phase 3b branding fields (additive, optional) ---
    logo = models.ImageField(
        upload_to="branding/org_logos/", null=True, blank=True,
        validators=[validate_logo_image],
    )
    default_sheet_heading = models.CharField(max_length=255, blank=True, default="")

    def __str__(self):
        return self.name


class OrganizationMembership(models.Model):
    ADMIN = "admin"
    MEMBER = "member"
    ROLE_CHOICES = [(ADMIN, "Admin"), (MEMBER, "Member")]

    ACTIVE = "active"
    INVITED = "invited"
    REMOVED = "removed"
    STATUS_CHOICES = [(ACTIVE, "Active"), (INVITED, "Invited"), (REMOVED, "Removed")]

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="memberships"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=MEMBER)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=ACTIVE)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "user"],
                name="uniq_org_membership",
            )
        ]
        indexes = [
            models.Index(fields=["organization", "status"], name="orgmembership_org_status_idx"),
        ]

    def __str__(self):
        return f"{self.user} @ {self.organization} ({self.role})"


class Invitation(models.Model):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="invitations"
    )
    email = models.EmailField()
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    role = models.CharField(
        max_length=10,
        choices=OrganizationMembership.ROLE_CHOICES,
        default=OrganizationMembership.MEMBER,
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Invite {self.email} → {self.organization}"


class AuditLog(models.Model):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="audit_logs"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    action = models.CharField(max_length=64)
    target_type = models.CharField(max_length=64, blank=True)
    target_id = models.IntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "created_at"], name="auditlog_org_created_idx"),
        ]

    def __str__(self):
        return f"{self.action} by {self.actor} in {self.organization}"


class ClassAccessGrant(models.Model):
    """An org admin's grant of a class (and, optionally, only specific subjects of
    it) to a member/teacher. ``all_subjects=True`` (default) → the whole class;
    otherwise only the linked ``subjects``. Org-only concept — personal/solo scope
    has no members, so grants never apply there."""

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="class_grants"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="class_grants"
    )
    class_group = models.ForeignKey(
        "assessments.ClassGroup", on_delete=models.CASCADE, related_name="access_grants"
    )
    all_subjects = models.BooleanField(default=True)
    subjects = models.ManyToManyField(
        "assessments.Subject", blank=True, related_name="access_grants"
    )
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "user", "class_group"],
                name="uniq_grant_org_user_class",
            )
        ]
        indexes = [
            models.Index(fields=["organization", "user"], name="grant_org_user_idx"),
            models.Index(fields=["class_group"], name="grant_class_idx"),
        ]

    def __str__(self):
        scope = "all subjects" if self.all_subjects else "narrowed"
        return f"{self.user} → {self.class_group} ({scope})"


class Role(models.Model):
    """An org-scoped named bundle of permission codes. System roles (Owner / Admin
    / Teacher / Viewer) are seeded per org; admins may add custom roles."""

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="roles")
    name = models.CharField(max_length=80)
    is_system = models.BooleanField(default=False)
    permissions = models.JSONField(default=list)  # list of permission codes
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "name"], name="uniq_role_org_name")
        ]

    def __str__(self):
        return f"{self.name} @ org {self.organization_id}"


class RoleBinding(models.Model):
    """Assigns a Role to a user, optionally SCOPED to a group subtree
    (scope_group=null → org-wide). The generalized per-class teacher grant."""

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="role_bindings")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="role_bindings")
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="bindings")
    scope_group = models.ForeignKey(
        "assessments.ClassGroup", null=True, blank=True, on_delete=models.CASCADE, related_name="role_bindings"
    )
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "user", "role", "scope_group"],
                name="uniq_rolebinding",
                nulls_distinct=False,
            )
        ]
        indexes = [models.Index(fields=["organization", "user"], name="rolebinding_org_user_idx")]


class PermissionGrant(models.Model):
    """Grants a single permission code to an INDIVIDUAL, optionally scoped to a
    group subtree (scope_group=null → org-wide)."""

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="permission_grants")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="permission_grants")
    permission = models.CharField(max_length=64)
    scope_group = models.ForeignKey(
        "assessments.ClassGroup", null=True, blank=True, on_delete=models.CASCADE, related_name="permission_grants"
    )
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "user", "permission", "scope_group"],
                name="uniq_permgrant",
                nulls_distinct=False,
            )
        ]
        indexes = [models.Index(fields=["organization", "user"], name="permgrant_org_user_idx")]
