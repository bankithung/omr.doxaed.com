"""Permission catalog — the single source of truth for RBAC permission codes.

A Role bundles a set of these codes. has_perm() checks a user's effective
permissions (role bindings + individual grants) against a code, optionally within
a group subtree. Org-wide permissions ignore the group scope.
"""

# ── Organization ──────────────────────────────────────────────────────────────
ORG_SETTINGS_MANAGE = "org.settings.manage"
ORG_BILLING_MANAGE = "org.billing.manage"
MEMBER_INVITE = "member.invite"
MEMBER_MANAGE = "member.manage"
ROLE_MANAGE = "role.manage"
AUDIT_VIEW = "audit.view"

# ── Structure (groups / subjects / students) ──────────────────────────────────
GROUP_CREATE = "group.create"
GROUP_EDIT = "group.edit"
GROUP_DELETE = "group.delete"
SUBJECT_MANAGE = "subject.manage"
STUDENT_MANAGE = "student.manage"

# ── Exams ─────────────────────────────────────────────────────────────────────
EXAM_CREATE = "exam.create"
EXAM_EDIT = "exam.edit"
EXAM_DELETE = "exam.delete"
EXAM_GENERATE = "exam.generate"
EXAM_SCAN = "exam.scan"
EXAM_GRADE = "exam.grade"
EXAM_RESULTS_VIEW = "exam.results.view"
EXAM_ANALYTICS_VIEW = "exam.analytics.view"
EXAM_SHARE = "exam.share"

# (code, human label, group) — drives the Roles & Permissions UI matrix.
CATALOG = [
    (ORG_SETTINGS_MANAGE, "Manage organization settings", "Organization"),
    (ORG_BILLING_MANAGE, "Manage billing & plan", "Organization"),
    (MEMBER_INVITE, "Invite members", "Organization"),
    (MEMBER_MANAGE, "Manage members", "Organization"),
    (ROLE_MANAGE, "Manage roles & permissions", "Organization"),
    (AUDIT_VIEW, "View the audit log", "Organization"),
    (GROUP_CREATE, "Create groups (classes/sections/…)", "Structure"),
    (GROUP_EDIT, "Edit groups", "Structure"),
    (GROUP_DELETE, "Delete groups", "Structure"),
    (SUBJECT_MANAGE, "Manage subjects", "Structure"),
    (STUDENT_MANAGE, "Manage students & rosters", "Structure"),
    (EXAM_CREATE, "Create exams", "Exams"),
    (EXAM_EDIT, "Edit exams & questions", "Exams"),
    (EXAM_DELETE, "Delete exams", "Exams"),
    (EXAM_GENERATE, "Generate & print sheets", "Exams"),
    (EXAM_SCAN, "Scan & auto-grade", "Exams"),
    (EXAM_GRADE, "Review & correct grading", "Exams"),
    (EXAM_RESULTS_VIEW, "View results", "Exams"),
    (EXAM_ANALYTICS_VIEW, "View analytics", "Exams"),
    (EXAM_SHARE, "Publish & share results", "Exams"),
]

ALL_CODES = [c for c, _, _ in CATALOG]
VALID_CODES = set(ALL_CODES)

# Permissions that are inherently org-wide — a group scope is irrelevant to them.
ORG_WIDE = {
    ORG_SETTINGS_MANAGE,
    ORG_BILLING_MANAGE,
    MEMBER_INVITE,
    MEMBER_MANAGE,
    ROLE_MANAGE,
    AUDIT_VIEW,
}

# Permissions that imply EDIT rights on a group's resources (used to rebuild
# can_edit_class / can_edit_test on top of has_perm).
EDIT_CODES = {
    GROUP_CREATE,
    GROUP_EDIT,
    GROUP_DELETE,
    SUBJECT_MANAGE,
    STUDENT_MANAGE,
    EXAM_CREATE,
    EXAM_EDIT,
    EXAM_DELETE,
    EXAM_GENERATE,
    EXAM_SCAN,
    EXAM_GRADE,
}

# Seeded per organization on creation. Each is fully editable, and admins can add
# custom roles. WHICH classes a role reaches is the binding's scope (org-wide for
# Supervisor/Office; assigned-groups for Teacher) — the codes say WHAT they can do.
_TEACHER = [
    GROUP_CREATE, GROUP_EDIT, SUBJECT_MANAGE, STUDENT_MANAGE,
    EXAM_CREATE, EXAM_EDIT, EXAM_DELETE, EXAM_GENERATE, EXAM_SCAN, EXAM_GRADE,
    EXAM_RESULTS_VIEW, EXAM_ANALYTICS_VIEW, EXAM_SHARE,
]

# Supervisor — runs all classes/exams across the org (bind org-wide), but no
# control over members, roles, billing or org settings.
_SUPERVISOR = [
    GROUP_CREATE, GROUP_EDIT, GROUP_DELETE, SUBJECT_MANAGE, STUDENT_MANAGE,
    EXAM_CREATE, EXAM_EDIT, EXAM_DELETE, EXAM_GENERATE, EXAM_SCAN, EXAM_GRADE,
    EXAM_RESULTS_VIEW, EXAM_ANALYTICS_VIEW, EXAM_SHARE, AUDIT_VIEW,
]

# Office / staff — manages members + students + structure across the org; does
# not create or grade exams, and no billing/roles/org-settings.
_OFFICE = [
    MEMBER_INVITE, MEMBER_MANAGE, GROUP_CREATE, GROUP_EDIT, SUBJECT_MANAGE,
    STUDENT_MANAGE, EXAM_RESULTS_VIEW, AUDIT_VIEW,
]

SYSTEM_ROLES = [
    ("Owner", list(ALL_CODES)),
    ("Admin", [c for c in ALL_CODES if c != ORG_BILLING_MANAGE]),
    ("Supervisor", _SUPERVISOR),
    ("Office", _OFFICE),
    ("Teacher", _TEACHER),
    ("Viewer", [EXAM_RESULTS_VIEW, EXAM_ANALYTICS_VIEW]),
]

# Roles whose holders are treated as org admins (full access, scope short-circuit).
ADMIN_ROLE_NAMES = {"Owner", "Admin"}
