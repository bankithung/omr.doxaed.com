from django.db import migrations


def seed_roles(apps, schema_editor):
    """Add the Supervisor/Office system roles (and refresh the rest) for every
    existing organization, idempotently."""
    from organizations.permissions_catalog import SYSTEM_ROLES

    Organization = apps.get_model("organizations", "Organization")
    Role = apps.get_model("organizations", "Role")
    for org in Organization.objects.all():
        for name, perms in SYSTEM_ROLES:
            Role.objects.update_or_create(
                organization=org,
                name=name,
                defaults={"is_system": True, "permissions": list(perms)},
            )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("organizations", "0009_organization_slug"),
    ]

    operations = [
        migrations.RunPython(seed_roles, noop),
    ]
