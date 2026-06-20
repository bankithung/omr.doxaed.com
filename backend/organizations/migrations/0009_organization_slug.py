from django.db import migrations, models
from django.utils.text import slugify


def populate_slugs(apps, schema_editor):
    """Backfill a unique slug for every existing organization."""
    Organization = apps.get_model("organizations", "Organization")
    seen = set()
    for org in Organization.objects.all().order_by("id"):
        base = slugify(org.name)[:55] or "org"
        slug = base
        n = 2
        while slug in seen:
            slug = f"{base}-{n}"
            n += 1
        seen.add(slug)
        org.slug = slug
        org.save(update_fields=["slug"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("organizations", "0008_role_rolebinding_permissiongrant_and_more"),
    ]

    operations = [
        # 1. add as a plain CharField (a SlugField here would create the pattern_ops
        #    "_like" index that the unique AlterField below also creates → collision).
        migrations.AddField(
            model_name="organization",
            name="slug",
            field=models.CharField(blank=True, default="", max_length=63),
        ),
        # 2. backfill unique slugs from the name
        migrations.RunPython(populate_slugs, noop),
        # 3. promote to a unique SlugField (creates the slug indexes once)
        migrations.AlterField(
            model_name="organization",
            name="slug",
            field=models.SlugField(blank=True, max_length=63, unique=True),
        ),
    ]
