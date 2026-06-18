"""
Product v2 Phase 5C — grandfather existing org data as org-visible.

Owner decision: no existing org member may lose access when folder-visibility
scoping is introduced. This migration makes ALL pre-existing org-owned data
remain visible to the whole organisation:

  1. For every existing org-scoped ClassGroup that already has a folder, ensure
     that folder carries an org-wide VIEW FolderShare.
  2. Existing org-scoped classes are mostly folder=NULL (loose). For each org,
     create ONE "General" Folder (organization-scoped, created_by = org owner)
     with an org-wide VIEW FolderShare, and reassign every existing org-scoped
     ClassGroup whose folder IS NULL into that General folder.

Solo (user-scoped) classes are untouched — folders never apply in solo scope.

Idempotent: re-running creates no duplicate General folders/shares and reassigns
no already-foldered class. Guards against an empty DB (no orgs / no classes).
"""
from django.db import migrations


GENERAL_FOLDER_NAME = "General"


def grandfather_forward(apps, schema_editor):
    ClassGroup = apps.get_model("assessments", "ClassGroup")
    Folder = apps.get_model("folders", "Folder")
    FolderShare = apps.get_model("folders", "FolderShare")
    Organization = apps.get_model("organizations", "Organization")

    db = schema_editor.connection.alias

    def ensure_org_share(folder):
        """Idempotently ensure an org-wide VIEW share exists for `folder`."""
        FolderShare.objects.using(db).get_or_create(
            folder=folder,
            shared_with=None,
            share_scope="org",
            defaults={
                "permission": "view",
                "created_by_id": folder.created_by_id,
            },
        )

    # (1) Org-scoped classes that ALREADY have a folder → ensure org-wide VIEW share.
    foldered = (
        ClassGroup.objects.using(db)
        .filter(organization__isnull=False, folder__isnull=False)
        .select_related("folder")
    )
    for cg in foldered:
        ensure_org_share(cg.folder)

    # (2) Loose org-scoped classes (folder IS NULL) → one General folder per org.
    # Only process orgs that actually have at least one loose org class.
    org_ids = (
        ClassGroup.objects.using(db)
        .filter(organization__isnull=False, folder__isnull=True)
        .values_list("organization_id", flat=True)
        .distinct()
    )

    for org_id in org_ids:
        org = Organization.objects.using(db).filter(pk=org_id).first()
        if org is None:
            continue
        creator_id = org.owner_id

        # Idempotent: reuse an existing org-scoped General folder if present.
        general = (
            Folder.objects.using(db)
            .filter(organization_id=org_id, name=GENERAL_FOLDER_NAME)
            .order_by("id")
            .first()
        )
        if general is None:
            general = Folder.objects.using(db).create(
                organization_id=org_id,
                user=None,
                created_by_id=creator_id,
                name=GENERAL_FOLDER_NAME,
                parent=None,
            )

        ensure_org_share(general)

        # Reassign every loose org-scoped class in this org into General.
        ClassGroup.objects.using(db).filter(
            organization_id=org_id, folder__isnull=True
        ).update(folder=general)


def grandfather_backward(apps, schema_editor):
    """Reverse: detach classes from auto-created General folders and remove the
    auto-created General folders + their org shares. We only remove General
    folders this migration could have created (org-scoped, name='General').
    Org shares on pre-existing user folders are left in place (harmless and we
    cannot reliably tell which we created)."""
    ClassGroup = apps.get_model("assessments", "ClassGroup")
    Folder = apps.get_model("folders", "Folder")
    FolderShare = apps.get_model("folders", "FolderShare")

    db = schema_editor.connection.alias

    general_folders = Folder.objects.using(db).filter(
        organization__isnull=False, name=GENERAL_FOLDER_NAME
    )
    general_ids = list(general_folders.values_list("id", flat=True))
    if general_ids:
        ClassGroup.objects.using(db).filter(folder_id__in=general_ids).update(
            folder=None
        )
        FolderShare.objects.using(db).filter(folder_id__in=general_ids).delete()
        general_folders.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("folders", "0001_initial"),
        ("assessments", "0010_classgroup_folder_subject_class_group_and_more"),
        ("organizations", "0002_auditlog_invitation_organizationmembership"),
    ]

    operations = [
        migrations.RunPython(grandfather_forward, grandfather_backward),
    ]
