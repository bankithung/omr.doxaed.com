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


# ---------------------------------------------------------------------------
# Task 2 tests: gateway + subscribe endpoint + signature-verified webhook
# ---------------------------------------------------------------------------

import hashlib
import hmac
import json
from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient


WEBHOOK_SECRET = "test_webhook_secret_xyz"

# Override Razorpay settings for all Task 2 tests.
RAZORPAY_TEST_SETTINGS = {
    "RAZORPAY_KEY_ID": "rzp_test_FAKE",
    "RAZORPAY_KEY_SECRET": "fake_secret",
    "RAZORPAY_WEBHOOK_SECRET": WEBHOOK_SECRET,
}


def _make_sig(body_bytes: bytes, secret: str = WEBHOOK_SECRET) -> str:
    """Compute the real HMAC-SHA256 signature (what Razorpay would send)."""
    return hmac.new(secret.encode(), body_bytes, hashlib.sha256).hexdigest()


def _webhook_body(event: str, sub_id: str, current_end: int | None = None) -> bytes:
    """Build a minimal Razorpay-style webhook JSON payload."""
    entity = {"id": sub_id}
    if current_end is not None:
        entity["current_end"] = current_end
    payload = {
        "event": event,
        "payload": {
            "subscription": {
                "entity": entity,
            }
        },
    }
    return json.dumps(payload).encode()


@override_settings(**RAZORPAY_TEST_SETTINGS)
class SubscribeEndpointTest(TestCase):
    """Tests for POST /api/v1/billing/organizations/{id}/subscribe/."""

    def setUp(self):
        self.client = APIClient()
        self.admin_user = make_user("sub_admin")
        self.member_user = make_user("sub_member")
        self.org = make_org(self.admin_user, "SubOrg")

        # Give member_user a non-admin membership.
        OrganizationMembership.objects.create(
            organization=self.org,
            user=self.member_user,
            role=OrganizationMembership.MEMBER,
            status=OrganizationMembership.ACTIVE,
        )

        self.team_plan = get_team_plan()
        get_free_plan()

        self.subscribe_url = f"/api/v1/billing/organizations/{self.org.pk}/subscribe/"

    # ------------------------------------------------------------------
    # Happy path: admin subscribes with a mocked gateway
    # ------------------------------------------------------------------

    def test_admin_subscribe_creates_subscription(self):
        """Admin POST subscribe (mocked gateway) → 201, Subscription(created) created."""
        self.client.force_authenticate(user=self.admin_user)
        fake_result = {
            "id": "sub_fake123",
            "short_url": "https://rzp.io/i/fake",
            "status": "created",
        }
        with patch("billing.gateway.create_subscription", return_value=fake_result):
            resp = self.client.post(
                self.subscribe_url,
                {"plan_code": "team"},
                format="json",
            )

        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data["subscription_id"], "sub_fake123")
        self.assertEqual(resp.data["short_url"], "https://rzp.io/i/fake")
        self.assertEqual(resp.data["key_id"], "rzp_test_FAKE")

        sub = Subscription.objects.get(organization=self.org)
        self.assertEqual(sub.status, Subscription.CREATED)
        self.assertEqual(sub.razorpay_subscription_id, "sub_fake123")
        self.assertEqual(sub.plan, self.team_plan)

    def test_subscribe_idempotent_update(self):
        """Calling subscribe again updates the existing Subscription row."""
        self.client.force_authenticate(user=self.admin_user)
        fake1 = {"id": "sub_first", "short_url": "", "status": "created"}
        fake2 = {"id": "sub_second", "short_url": "", "status": "created"}

        with patch("billing.gateway.create_subscription", return_value=fake1):
            self.client.post(self.subscribe_url, {"plan_code": "team"}, format="json")

        with patch("billing.gateway.create_subscription", return_value=fake2):
            resp = self.client.post(self.subscribe_url, {"plan_code": "team"}, format="json")

        self.assertEqual(resp.status_code, 201)
        # Still only one Subscription for the org.
        self.assertEqual(Subscription.objects.filter(organization=self.org).count(), 1)
        sub = Subscription.objects.get(organization=self.org)
        self.assertEqual(sub.razorpay_subscription_id, "sub_second")

    # ------------------------------------------------------------------
    # Non-admin → 403
    # ------------------------------------------------------------------

    def test_non_admin_subscribe_forbidden(self):
        """A member (non-admin) gets a 403 when trying to subscribe."""
        self.client.force_authenticate(user=self.member_user)
        fake_result = {"id": "sub_nope", "short_url": "", "status": "created"}
        with patch("billing.gateway.create_subscription", return_value=fake_result):
            resp = self.client.post(
                self.subscribe_url,
                {"plan_code": "team"},
                format="json",
            )
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(Subscription.objects.filter(organization=self.org).exists())

    def test_unauthenticated_subscribe_forbidden(self):
        """Unauthenticated request → 401."""
        resp = self.client.post(self.subscribe_url, {"plan_code": "team"}, format="json")
        self.assertIn(resp.status_code, (401, 403))

    # ------------------------------------------------------------------
    # Bad plan_code → 400
    # ------------------------------------------------------------------

    def test_bad_plan_code_returns_400(self):
        """Unknown plan_code → 400 with detail message."""
        self.client.force_authenticate(user=self.admin_user)
        resp = self.client.post(
            self.subscribe_url,
            {"plan_code": "nonexistent"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400, resp.data)
        self.assertIn("plan_code", resp.data["detail"])

    def test_missing_plan_code_returns_400(self):
        """Empty plan_code → 400."""
        self.client.force_authenticate(user=self.admin_user)
        resp = self.client.post(self.subscribe_url, {}, format="json")
        self.assertEqual(resp.status_code, 400)

    # ------------------------------------------------------------------
    # Non-member of org → 403
    # ------------------------------------------------------------------

    def test_non_member_subscribe_forbidden(self):
        """User not in the org at all → 403."""
        outsider = make_user("outsider_sub")
        self.client.force_authenticate(user=outsider)
        resp = self.client.post(
            self.subscribe_url,
            {"plan_code": "team"},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)


@override_settings(**RAZORPAY_TEST_SETTINGS)
class WebhookSignatureTest(TestCase):
    """Tests for POST /api/v1/billing/webhook/."""

    def setUp(self):
        self.client = APIClient()
        self.webhook_url = "/api/v1/billing/webhook/"

        # Create a Subscription in 'created' state so webhook can update it.
        self.user = make_user("wh_user")
        self.org = make_org(self.user, "WebhookOrg")
        get_free_plan()
        self.team_plan = get_team_plan()
        self.sub = Subscription.objects.create(
            organization=self.org,
            plan=self.team_plan,
            status=Subscription.CREATED,
            razorpay_subscription_id="sub_wh_abc",
        )

    # ------------------------------------------------------------------
    # subscription.activated → status = active
    # ------------------------------------------------------------------

    def test_valid_signature_activated_sets_active(self):
        """Valid HMAC signature + subscription.activated → Subscription becomes active."""
        body = _webhook_body("subscription.activated", "sub_wh_abc")
        sig = _make_sig(body)
        resp = self.client.post(
            self.webhook_url,
            data=body,
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE=sig,
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, Subscription.ACTIVE)

    def test_valid_signature_charged_sets_active(self):
        """subscription.charged event also sets status to active."""
        body = _webhook_body("subscription.charged", "sub_wh_abc")
        sig = _make_sig(body)
        resp = self.client.post(
            self.webhook_url,
            data=body,
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE=sig,
        )
        self.assertEqual(resp.status_code, 200)
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, Subscription.ACTIVE)

    def test_activated_stores_current_period_end(self):
        """subscription.activated with current_end timestamp → stored on the Subscription."""
        import time

        future_ts = int(time.time()) + 30 * 86400  # 30 days from now
        body = _webhook_body("subscription.activated", "sub_wh_abc", current_end=future_ts)
        sig = _make_sig(body)
        resp = self.client.post(
            self.webhook_url,
            data=body,
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE=sig,
        )
        self.assertEqual(resp.status_code, 200)
        self.sub.refresh_from_db()
        self.assertIsNotNone(self.sub.current_period_end)

    # ------------------------------------------------------------------
    # subscription.cancelled → status = canceled
    # ------------------------------------------------------------------

    def test_valid_signature_cancelled_sets_canceled(self):
        """subscription.cancelled → Subscription becomes canceled."""
        # First activate it.
        self.sub.status = Subscription.ACTIVE
        self.sub.save(update_fields=["status"])

        body = _webhook_body("subscription.cancelled", "sub_wh_abc")
        sig = _make_sig(body)
        resp = self.client.post(
            self.webhook_url,
            data=body,
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE=sig,
        )
        self.assertEqual(resp.status_code, 200)
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, Subscription.CANCELED)

    # ------------------------------------------------------------------
    # subscription.halted → status = past_due
    # ------------------------------------------------------------------

    def test_valid_signature_halted_sets_past_due(self):
        """subscription.halted → Subscription becomes past_due."""
        body = _webhook_body("subscription.halted", "sub_wh_abc")
        sig = _make_sig(body)
        resp = self.client.post(
            self.webhook_url,
            data=body,
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE=sig,
        )
        self.assertEqual(resp.status_code, 200)
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, Subscription.PAST_DUE)

    # ------------------------------------------------------------------
    # INVALID signature → 400 (KEY security test)
    # ------------------------------------------------------------------

    def test_invalid_signature_returns_400(self):
        """Wrong HMAC signature → 400 and Subscription status unchanged."""
        original_status = self.sub.status
        body = _webhook_body("subscription.activated", "sub_wh_abc")
        bad_sig = "deadbeef" * 8  # wrong signature

        resp = self.client.post(
            self.webhook_url,
            data=body,
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE=bad_sig,
        )
        self.assertEqual(resp.status_code, 400)
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, original_status)

    def test_missing_signature_returns_400(self):
        """Missing X-Razorpay-Signature header → 400."""
        body = _webhook_body("subscription.activated", "sub_wh_abc")
        resp = self.client.post(
            self.webhook_url,
            data=body,
            content_type="application/json",
            # no HTTP_X_RAZORPAY_SIGNATURE header
        )
        self.assertEqual(resp.status_code, 400)
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, Subscription.CREATED)

    def test_tampered_body_returns_400(self):
        """Valid signature computed over original body, but body was tampered → 400."""
        original_body = _webhook_body("subscription.activated", "sub_wh_abc")
        sig = _make_sig(original_body)

        # Tamper: change the subscription ID in the body.
        tampered_body = _webhook_body("subscription.activated", "sub_DIFFERENT")

        resp = self.client.post(
            self.webhook_url,
            data=tampered_body,
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE=sig,
        )
        self.assertEqual(resp.status_code, 400)

    # ------------------------------------------------------------------
    # Idempotency
    # ------------------------------------------------------------------

    def test_duplicate_activated_event_idempotent(self):
        """Delivering the same activation event twice is safe."""
        body = _webhook_body("subscription.activated", "sub_wh_abc")
        sig = _make_sig(body)

        for _ in range(2):
            resp = self.client.post(
                self.webhook_url,
                data=body,
                content_type="application/json",
                HTTP_X_RAZORPAY_SIGNATURE=sig,
            )
            self.assertEqual(resp.status_code, 200)

        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, Subscription.ACTIVE)

    # ------------------------------------------------------------------
    # Unknown subscription ID → 200 (ack gracefully)
    # ------------------------------------------------------------------

    def test_unknown_subscription_id_returns_200(self):
        """Webhook for a subscription ID we don't know → 200 (acked, ignored)."""
        body = _webhook_body("subscription.activated", "sub_UNKNOWN_ID")
        sig = _make_sig(body)
        resp = self.client.post(
            self.webhook_url,
            data=body,
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE=sig,
        )
        self.assertEqual(resp.status_code, 200)
        # Our subscription is unaffected.
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, Subscription.CREATED)

    # ------------------------------------------------------------------
    # verify_webhook_signature unit test
    # ------------------------------------------------------------------

    def test_verify_webhook_signature_correct(self):
        """Unit test: verify_webhook_signature returns True for a correct signature."""
        from billing.gateway import verify_webhook_signature

        body = b"hello world"
        sig = hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
        self.assertTrue(verify_webhook_signature(body, sig))

    def test_verify_webhook_signature_wrong(self):
        """Unit test: verify_webhook_signature returns False for a wrong signature."""
        from billing.gateway import verify_webhook_signature

        body = b"hello world"
        self.assertFalse(verify_webhook_signature(body, "wrongsig"))

    def test_verify_webhook_signature_empty(self):
        """Unit test: verify_webhook_signature returns False for empty signature."""
        from billing.gateway import verify_webhook_signature

        body = b"hello world"
        self.assertFalse(verify_webhook_signature(body, ""))
