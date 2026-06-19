"""Backfill the system roles for every existing organization."""
from django.core.management.base import BaseCommand

from organizations.models import Organization
from organizations.role_seed import seed_org_roles


class Command(BaseCommand):
    help = "Seed system roles (Owner/Admin/Teacher/Viewer) for every organization."

    def handle(self, *args, **options):
        n = 0
        for org in Organization.objects.select_related("owner"):
            seed_org_roles(org, org.owner)
            n += 1
        self.stdout.write(self.style.SUCCESS(f"Seeded roles for {n} organization(s)."))
