"""DEV/admin tool: activate a plan for an organization by slug, bypassing payment.

This is a CLI command (requires server access) — NOT a web endpoint — so it is
not a payment-bypass vector. Use it to exercise plan limits locally without a
configured Razorpay gateway.

    manage.py set_org_plan <slug> <free|team|business|enterprise>
"""
from django.core.management.base import BaseCommand, CommandError

from billing.models import Plan, Subscription
from organizations.models import Organization


class Command(BaseCommand):
    help = "DEV: set an organization's plan by slug (bypasses payment; local testing only)."

    def add_arguments(self, parser):
        parser.add_argument("slug")
        parser.add_argument("code", help="Plan code: free | team | business | enterprise")

    def handle(self, *args, **opts):
        org = Organization.objects.filter(slug=opts["slug"]).first()
        if not org:
            raise CommandError(f"No organization with slug '{opts['slug']}'.")

        code = opts["code"]
        if code == "free":
            Subscription.objects.filter(organization=org).delete()
            self.stdout.write(self.style.SUCCESS(f"{org.name} -> Free (subscription removed)"))
            return

        plan = Plan.objects.filter(code=code).first()
        if not plan:
            raise CommandError(f"No plan with code '{code}'.")

        Subscription.objects.update_or_create(
            organization=org,
            defaults={
                "plan": plan,
                "status": Subscription.ACTIVE,
                "seats_purchased": plan.seat_limit or 1,
            },
        )
        self.stdout.write(self.style.SUCCESS(f"{org.name} -> {plan.name} (active)"))
