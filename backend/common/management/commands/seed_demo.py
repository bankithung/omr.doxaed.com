"""Seed a demo account with enough content to click through the whole product.

    python manage.py seed_demo

Idempotent: running it twice updates in place rather than duplicating. Refuses
to run unless DEBUG is on, so it can never create a known password in prod.
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from assessments.models import ClassGroup, Question, Section, Test
from organizations.models import Organization, OrganizationMembership
from rosters.models import Roster, Student

EMAIL = "demo@doxaed.com"
PASSWORD = "DemoPass123!"
ORG_SLUG = "demo-school"

STUDENTS = [
    "Asha Rao", "Rahul Nair", "Meera Singh", "Dev Patel", "Kiran Das",
    "Nisha Iyer", "Arjun Menon", "Priya Shah", "Vikram Rao", "Sana Khan",
    "Imran Sheikh", "Divya Pillai", "Rohit Verma", "Anjali Bose", "Karan Gill",
]


class Command(BaseCommand):
    help = "Seed a demo user, organization, class, roster and exam for local development."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Allow seeding even when DEBUG is False. Never use this on a real deployment.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG and not options["force"]:
            raise CommandError(
                "seed_demo creates an account with a known password and only runs with DEBUG=True. "
                "Pass --force if you are certain this is a throwaway environment."
            )

        User = get_user_model()
        user, created = User.objects.get_or_create(email=EMAIL, defaults={"is_active": True})
        user.set_password(PASSWORD)
        user.is_active = True
        if hasattr(user, "is_email_verified"):
            user.is_email_verified = True
        if hasattr(user, "full_name") and not user.full_name:
            user.full_name = "Demo Teacher"
        user.save()
        self._say(f"user {EMAIL}", created)

        org, created = Organization.objects.get_or_create(
            slug=ORG_SLUG,
            defaults=dict(name="Demo School", owner=user, type="school"),
        )
        OrganizationMembership.objects.get_or_create(
            organization=org, user=user, defaults=dict(role="admin", status="active")
        )
        self._say(f"organization {org.slug}", created)

        # Owner scope is user XOR organization: everything below belongs to the org.
        scope = dict(user=None, organization=org)

        cls, created = ClassGroup.objects.get_or_create(
            name="Grade 10",
            parent=None,
            **scope,
            defaults=dict(
                created_by=user,
                kind_label="Class",
                description="Senior secondary cohort",
            ),
        )
        self._say(f"class {cls.name}", created)

        for idx, label in enumerate(["Section A", "Section B"], start=1):
            ClassGroup.objects.get_or_create(
                name=label,
                parent=cls,
                **scope,
                defaults=dict(created_by=user, kind_label="Section", order=idx),
            )
        self._say("sections A and B", True)

        roster, created = Roster.objects.get_or_create(
            name="Grade 10 roster",
            **scope,
            defaults=dict(created_by=user, class_group=cls),
        )
        for i, name in enumerate(STUDENTS, start=1):
            Student.objects.get_or_create(
                roster=roster, roll_number=f"{i:03d}", defaults=dict(full_name=name)
            )
        self._say(f"roster with {roster.students.count()} students", created)

        test, created = Test.objects.get_or_create(
            title="Midterm Physics",
            **scope,
            defaults=dict(created_by=user, class_group=cls, status="ready"),
        )
        section, _ = Section.objects.get_or_create(
            test=test,
            label="Section A",
            defaults=dict(order_index=1, q_start=1, q_end=10),
        )
        for i in range(1, 11):
            Question.objects.get_or_create(
                test=test, order_index=i, defaults=dict(section=section)
            )
        self._say(f"exam {test.title} with {test.questions.count()} questions", created)

        for cmd in ("seed_plans", "seed_roles"):
            try:
                call_command(cmd, verbosity=0)
            except Exception:  # optional, never block the demo seed
                pass

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("  demo data ready"))
        self.stdout.write(f"    sign in : {EMAIL} / {PASSWORD}")
        self.stdout.write(f"    org     : /org/{org.slug}")

    def _say(self, what, created):
        verb = "created" if created else "updated"
        self.stdout.write(f"  {verb:>7}  {what}")
