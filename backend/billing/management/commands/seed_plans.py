"""
Idempotently seed the four billing plan tiers.
Run once after migrations:  python manage.py seed_plans
"""

from django.core.management.base import BaseCommand

from billing.models import Plan

PLANS = [
    {
        "code": Plan.FREE,
        "name": "Free",
        "price_inr": "0.00",
        "seat_limit": 1,
        "students_per_generation_limit": 10,
        "generations_per_day_limit": 5,
        "monthly_scan_limit": 100,
    },
    {
        "code": Plan.TEAM,  # internal code "team"; display name "Pro"
        "name": "Pro",
        "price_inr": "1000.00",
        "seat_limit": 5,
        "students_per_generation_limit": None,  # unlimited
        "generations_per_day_limit": None,
        "monthly_scan_limit": 2000,
    },
    {
        "code": Plan.BUSINESS,
        "name": "Business",
        "price_inr": "2000.00",
        "seat_limit": 20,
        "students_per_generation_limit": None,
        "generations_per_day_limit": None,
        "monthly_scan_limit": 10000,
    },
    {
        "code": Plan.ENTERPRISE,
        "name": "Enterprise",
        "price_inr": "0.00",
        "seat_limit": None,
        "students_per_generation_limit": None,
        "generations_per_day_limit": None,
        "monthly_scan_limit": None,
    },
]


class Command(BaseCommand):
    help = "Idempotently seed the four billing plan tiers (free/team/business/enterprise)."

    def handle(self, *args, **options):
        for data in PLANS:
            code = data.pop("code")
            plan, created = Plan.objects.update_or_create(code=code, defaults=data)
            verb = "Created" if created else "Updated"
            self.stdout.write(f"  {verb}: {plan.code} - {plan.name}")
            data["code"] = code  # restore for reuse safety
        self.stdout.write(self.style.SUCCESS("Plans seeded successfully."))
