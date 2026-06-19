"""Seed the system roles for an organization + bind the owner to Owner."""
from organizations.models import Role, RoleBinding
from organizations.permissions_catalog import SYSTEM_ROLES


def seed_org_roles(org, owner=None):
    """Idempotently create the org's system roles (Owner/Admin/Teacher/Viewer).
    When `owner` is given, bind them org-wide to the Owner role."""
    roles = {}
    for name, perms in SYSTEM_ROLES:
        role, _ = Role.objects.update_or_create(
            organization=org,
            name=name,
            defaults={"is_system": True, "permissions": list(perms)},
        )
        roles[name] = role
    if owner is not None:
        RoleBinding.objects.get_or_create(
            organization=org,
            user=owner,
            role=roles["Owner"],
            scope_group=None,
            defaults={"granted_by": owner},
        )
    return roles
