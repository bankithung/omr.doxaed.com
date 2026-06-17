"""
TDD tests for Phase 7, Task 1:
  - Plan / Subscription models
  - billing.limits service (per-org quota enforcement)
  - Per-org GenerationEvent / ScanEvent
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from billing.limits import (
    can_add_seat,
    can_generate,
    can_scan,
    generations_today,
    org_plan,
    scans_this_month,
    seat_count,
)
from billing.models import Plan, Subscription
from omr.models import GenerationEvent, ScanEvent
from organizations.models import Organization, OrganizationMembership

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_user(tag):
    """Create a user identified by email; tag is used to make the email unique."""
    return User.objects.create_user(
        email=f"{tag}@test.com", password="pass"
    )


def make_org(owner, name="TestOrg"):
    org = Organization.objects.create(name=name, owner=owner)
    OrganizationMembership.objects.create(
        organization=org,
        user=owner,
        role=OrganizationMembership.ADMIN,
        status=OrganizationMembership.ACTIVE,
    )
    return org


_test_counter = 0


def make_test(user):
    """Create a minimal assessments.Test for the given solo user."""
    global _test_counter
    _test_counter += 1
    from assessments.models import ClassGroup, Test

    cg = ClassGroup.objects.create(name=f"CG{_test_counter}", user=user, created_by=user)
    return Test.objects.create(
        title=f"T{_test_counter}",
        user=user,
        class_group=cg,
        created_by=user,
    )


def get_free_plan():
    plan, _ = Plan.objects.get_or_create(
        code=Plan.FREE,
        defaults={
            "name": "Free",
            "price_inr": "0.00",
            "seat_limit": 1,
            "students_per_generation_limit": 10,
            "generations_per_day_limit": 5,
            "monthly_scan_limit": 50,
        },
    )
    return plan


def get_team_plan():
    plan, _ = Plan.objects.get_or_create(
        code=Plan.TEAM,
        defaults={
            "name": "Team",
            "price_inr": "500.00",
            "seat_limit": 50,
            "students_per_generation_limit": None,
            "generations_per_day_limit": None,
            "monthly_scan_limit": 5000,
        },
    )
    return plan


# ---------------------------------------------------------------------------
# Test: org_plan resolution
# ---------------------------------------------------------------------------


class OrgPlanResolutionTest(TestCase):
    def setUp(self):
        self.user = make_user("alice")
        self.org = make_org(self.user)
        self.free = get_free_plan()
        self.team = get_team_plan()

    def test_no_subscription_returns_free(self):
        """org with no Subscription → free plan."""
        self.assertEqual(org_plan(self.org), self.free)

    def test_created_subscription_returns_free(self):
        """org with a 'created' (not yet active) Subscription → free plan."""
        Subscription.objects.create(
            organization=self.org,
            plan=self.team,
            status=Subscription.CREATED,
        )
        self.assertEqual(org_plan(self.org), self.free)

    def test_canceled_subscription_returns_free(self):
        """org with a 'canceled' Subscription → free plan."""
        Subscription.objects.create(
            organization=self.org,
            plan=self.team,
            status=Subscription.CANCELED,
        )
        self.assertEqual(org_plan(self.org), self.free)

    def test_past_due_subscription_returns_free(self):
        """org with a 'past_due' Subscription → free plan."""
        Subscription.objects.create(
            organization=self.org,
            plan=self.team,
            status=Subscription.PAST_DUE,
        )
        self.assertEqual(org_plan(self.org), self.free)

    def test_active_subscription_returns_plan(self):
        """org with an 'active' Subscription → that subscription's plan."""
        Subscription.objects.create(
            organization=self.org,
            plan=self.team,
            status=Subscription.ACTIVE,
        )
        self.assertEqual(org_plan(self.org), self.team)


# ---------------------------------------------------------------------------
# Test: seat gate (free plan — seat_limit=1)
# ---------------------------------------------------------------------------


class FreePlanSeatGateTest(TestCase):
    def setUp(self):
        self.user = make_user("bob")
        self.org = make_org(self.user)
        get_free_plan()  # ensure free plan exists

    def test_seat_count_is_one(self):
        """One admin membership → seat_count = 1."""
        self.assertEqual(seat_count(self.org), 1)

    def test_can_add_seat_false_at_limit(self):
        """Free plan seat_limit=1; already 1 active member → can_add_seat False."""
        self.assertFalse(can_add_seat(self.org))

    def test_can_add_seat_true_when_below_limit(self):
        """Remove the membership → 0 active → can_add_seat True on free plan."""
        OrganizationMembership.objects.filter(organization=self.org).update(
            status=OrganizationMembership.REMOVED
        )
        self.assertTrue(can_add_seat(self.org))


# ---------------------------------------------------------------------------
# Test: generation gate (free plan — 10 students/gen, 5 gens/day)
# ---------------------------------------------------------------------------


class FreePlanGenerationGateTest(TestCase):
    def setUp(self):
        self.user = make_user("carol")
        self.org = make_org(self.user)
        get_free_plan()
        self.assessment = make_test(self.user)

    def _make_gen_event(self):
        GenerationEvent.objects.create(
            user=self.user,
            test=self.assessment,
            organization=self.org,
        )

    def test_can_generate_ok(self):
        """0 events today, 5 students → allowed."""
        self.assertTrue(can_generate(self.org, 5))

    def test_can_generate_false_too_many_students(self):
        """11 students > limit of 10 → denied."""
        self.assertFalse(can_generate(self.org, 11))

    def test_can_generate_exactly_at_student_limit(self):
        """Exactly 10 students = limit → allowed."""
        self.assertTrue(can_generate(self.org, 10))

    def test_can_generate_false_after_daily_cap(self):
        """After 5 GenerationEvents today → 6th attempt denied."""
        for _ in range(5):
            self._make_gen_event()
        self.assertEqual(generations_today(self.org), 5)
        self.assertFalse(can_generate(self.org, 5))

    def test_generations_today_counts_only_today(self):
        """Events from yesterday don't count toward today's quota."""
        yesterday = timezone.now() - timedelta(days=1)
        event = GenerationEvent.objects.create(
            user=self.user,
            test=self.assessment,
            organization=self.org,
        )
        GenerationEvent.objects.filter(pk=event.pk).update(created_at=yesterday)
        self.assertEqual(generations_today(self.org), 0)
        self.assertTrue(can_generate(self.org, 5))

    def test_generations_today_per_org_not_user(self):
        """Events for a different org don't count toward this org's daily quota."""
        user2 = make_user("dave")
        other_org = make_org(user2, "OtherOrg")
        test2 = make_test(user2)
        for _ in range(5):
            GenerationEvent.objects.create(
                user=user2,
                test=test2,
                organization=other_org,
            )
        self.assertEqual(generations_today(self.org), 0)
        self.assertTrue(can_generate(self.org, 5))


# ---------------------------------------------------------------------------
# Test: scan gate (free plan — monthly_scan_limit=50)
# ---------------------------------------------------------------------------


class FreePlanScanGateTest(TestCase):
    def setUp(self):
        self.user = make_user("eve")
        self.org = make_org(self.user)
        get_free_plan()

    def _make_scan_event(self):
        ScanEvent.objects.create(user=self.user, organization=self.org)

    def test_can_scan_ok(self):
        """0 scans this month → allowed."""
        self.assertTrue(can_scan(self.org))

    def test_scans_this_month_count(self):
        """Creating 3 ScanEvents → scans_this_month = 3."""
        for _ in range(3):
            self._make_scan_event()
        self.assertEqual(scans_this_month(self.org), 3)

    def test_can_scan_false_after_monthly_cap(self):
        """After 50 ScanEvents → can_scan returns False."""
        for _ in range(50):
            self._make_scan_event()
        self.assertFalse(can_scan(self.org))

    def test_can_scan_true_at_49(self):
        """49 scans = still under limit of 50."""
        for _ in range(49):
            self._make_scan_event()
        self.assertTrue(can_scan(self.org))

    def test_scans_previous_month_ignored(self):
        """Scans from a previous month don't count toward this month's quota."""
        last_month = timezone.now() - timedelta(days=32)
        event = ScanEvent.objects.create(user=self.user, organization=self.org)
        ScanEvent.objects.filter(pk=event.pk).update(created_at=last_month)
        self.assertEqual(scans_this_month(self.org), 0)
        self.assertTrue(can_scan(self.org))

    def test_scans_per_org_isolated(self):
        """Scans in another org don't affect this org's scan count."""
        user2 = make_user("frank")
        other_org = make_org(user2, "OtherOrg2")
        for _ in range(50):
            ScanEvent.objects.create(user=user2, organization=other_org)
        self.assertEqual(scans_this_month(self.org), 0)
        self.assertTrue(can_scan(self.org))


# ---------------------------------------------------------------------------
# Test: team plan — higher limits
# ---------------------------------------------------------------------------


class TeamPlanLimitsTest(TestCase):
    def setUp(self):
        self.user = make_user("grace")
        self.org = make_org(self.user)
        self.team = get_team_plan()
        get_free_plan()

        Subscription.objects.create(
            organization=self.org,
            plan=self.team,
            status=Subscription.ACTIVE,
        )
        self.assessment = make_test(self.user)

    def test_org_plan_is_team(self):
        self.assertEqual(org_plan(self.org), self.team)

    def test_can_add_seat_true_for_team(self):
        """Team plan: seat_limit=50; only 1 member → can add more."""
        self.assertTrue(can_add_seat(self.org))

    def test_can_add_seat_true_up_to_49(self):
        """49 active members total → still can add one more (limit=50)."""
        for i in range(48):
            u = make_user(f"tmember{i}")
            OrganizationMembership.objects.create(
                organization=self.org,
                user=u,
                role=OrganizationMembership.MEMBER,
                status=OrganizationMembership.ACTIVE,
            )
        self.assertEqual(seat_count(self.org), 49)
        self.assertTrue(can_add_seat(self.org))

    def test_can_generate_unlimited_students(self):
        """Team plan: no students_per_generation_limit → large batch allowed."""
        self.assertTrue(can_generate(self.org, 500))

    def test_can_generate_no_daily_cap(self):
        """Team plan: no daily generation cap → allowed after many events."""
        for _ in range(100):
            GenerationEvent.objects.create(
                user=self.user,
                test=self.assessment,
                organization=self.org,
            )
        self.assertTrue(can_generate(self.org, 100))

    def test_scan_limit_is_5000(self):
        """Team plan: monthly_scan_limit=5000."""
        self.assertEqual(self.team.monthly_scan_limit, 5000)

    def test_can_scan_team_up_to_5000(self):
        """50 scans well below team limit of 5000 → can_scan True."""
        for _ in range(50):
            ScanEvent.objects.create(user=self.user, organization=self.org)
        self.assertTrue(can_scan(self.org))


# ---------------------------------------------------------------------------
# Test: Subscription model fields
# ---------------------------------------------------------------------------


class SubscriptionModelTest(TestCase):
    def setUp(self):
        self.user = make_user("henry")
        self.org = make_org(self.user)
        self.free = get_free_plan()
        self.team = get_team_plan()

    def test_subscription_default_status_created(self):
        sub = Subscription.objects.create(organization=self.org, plan=self.team)
        self.assertEqual(sub.status, Subscription.CREATED)

    def test_subscription_active_status(self):
        sub = Subscription.objects.create(
            organization=self.org, plan=self.team, status=Subscription.ACTIVE
        )
        self.assertEqual(sub.status, Subscription.ACTIVE)

    def test_one_subscription_per_org(self):
        """OneToOne constraint: a second Subscription for same org raises IntegrityError."""
        from django.db import IntegrityError

        Subscription.objects.create(organization=self.org, plan=self.free)
        with self.assertRaises(IntegrityError):
            Subscription.objects.create(organization=self.org, plan=self.team)

    def test_subscription_str(self):
        sub = Subscription.objects.create(
            organization=self.org, plan=self.team, status=Subscription.ACTIVE
        )
        self.assertIn("team", str(sub))
        self.assertIn("active", str(sub))


# ---------------------------------------------------------------------------
# Test: Plan model values
# ---------------------------------------------------------------------------


class PlanModelTest(TestCase):
    def setUp(self):
        get_free_plan()
        get_team_plan()
        Plan.objects.get_or_create(
            code=Plan.BUSINESS,
            defaults={
                "name": "Business",
                "price_inr": "1000.00",
                "seat_limit": 200,
                "monthly_scan_limit": 20000,
            },
        )
        Plan.objects.get_or_create(
            code=Plan.ENTERPRISE,
            defaults={
                "name": "Enterprise",
                "price_inr": "0.00",
                "seat_limit": None,
                "monthly_scan_limit": None,
            },
        )

    def test_free_plan_limits(self):
        free = Plan.objects.get(code=Plan.FREE)
        self.assertEqual(free.seat_limit, 1)
        self.assertEqual(free.students_per_generation_limit, 10)
        self.assertEqual(free.generations_per_day_limit, 5)
        self.assertEqual(free.monthly_scan_limit, 50)

    def test_team_plan_limits(self):
        team = Plan.objects.get(code=Plan.TEAM)
        self.assertEqual(team.seat_limit, 50)
        self.assertIsNone(team.students_per_generation_limit)
        self.assertIsNone(team.generations_per_day_limit)
        self.assertEqual(team.monthly_scan_limit, 5000)

    def test_business_plan_limits(self):
        biz = Plan.objects.get(code=Plan.BUSINESS)
        self.assertEqual(biz.seat_limit, 200)
        self.assertEqual(biz.monthly_scan_limit, 20000)

    def test_enterprise_plan_unlimited(self):
        ent = Plan.objects.get(code=Plan.ENTERPRISE)
        self.assertIsNone(ent.seat_limit)
        self.assertIsNone(ent.monthly_scan_limit)


# ---------------------------------------------------------------------------
# Test: per-org GenerationEvent / ScanEvent FK
# ---------------------------------------------------------------------------


class PerOrgEventFKTest(TestCase):
    def setUp(self):
        self.user = make_user("irene")
        self.org = make_org(self.user)
        get_free_plan()
        self.test_obj = make_test(self.user)

    def test_generation_event_has_organization_fk(self):
        event = GenerationEvent.objects.create(
            user=self.user,
            test=self.test_obj,
            organization=self.org,
        )
        self.assertEqual(event.organization, self.org)

    def test_generation_event_org_nullable(self):
        """Solo (no org) GenerationEvent: organization can be null."""
        event = GenerationEvent.objects.create(
            user=self.user,
            test=self.test_obj,
        )
        self.assertIsNone(event.organization)

    def test_scan_event_created(self):
        event = ScanEvent.objects.create(
            user=self.user,
            organization=self.org,
        )
        self.assertEqual(event.organization, self.org)
        self.assertEqual(event.user, self.user)

    def test_scan_event_test_nullable(self):
        event = ScanEvent.objects.create(user=self.user, organization=self.org)
        self.assertIsNone(event.test)

    def test_scan_event_org_nullable(self):
        """Solo scan: organization can be null."""
        event = ScanEvent.objects.create(user=self.user)
        self.assertIsNone(event.organization)
