"""
Plan-limits service — per-org quota enforcement.

All functions accept an Organization instance.  'null' limit = unlimited.
"""

from django.utils import timezone

from billing.models import Plan, Subscription
from omr.models import GenerationEvent, ScanEvent
from organizations.models import OrganizationMembership


# ---------------------------------------------------------------------------
# Plan resolution
# ---------------------------------------------------------------------------


def _get_free_plan() -> Plan:
    """Return the free Plan, creating it with defaults if it has somehow been deleted."""
    plan, _ = Plan.objects.get_or_create(
        code=Plan.FREE,
        defaults={
            "name": "Free",
            "price_inr": "0.00",
            "seat_limit": 1,
            "students_per_generation_limit": 10,
            "generations_per_day_limit": 5,
            "monthly_scan_limit": 100,
        },
    )
    return plan


def org_plan(org) -> Plan:
    """Return the Plan that governs *org*.

    Returns the active Subscription's plan when the org has an active subscription;
    otherwise returns the free plan.
    """
    try:
        sub = org.subscription
    except Subscription.DoesNotExist:
        return _get_free_plan()

    if sub.status == Subscription.ACTIVE:
        return sub.plan

    return _get_free_plan()


# ---------------------------------------------------------------------------
# Seat gate
# ---------------------------------------------------------------------------


def seat_count(org) -> int:
    """Number of active members in the org."""
    return OrganizationMembership.objects.filter(
        organization=org,
        status=OrganizationMembership.ACTIVE,
    ).count()


def can_add_seat(org) -> bool:
    """True if the org may add another member under its current plan."""
    plan = org_plan(org)
    if plan.seat_limit is None:
        return True
    return seat_count(org) < plan.seat_limit


# ---------------------------------------------------------------------------
# Generation gates
# ---------------------------------------------------------------------------


def generations_today(org) -> int:
    """Number of GenerationEvents recorded for *org* today (UTC calendar day)."""
    today = timezone.now().date()
    return GenerationEvent.objects.filter(
        organization=org,
        created_at__date=today,
    ).count()


def can_generate(org, n_students: int) -> bool:
    """True if *org* may run one more generation for *n_students* students.

    Checks both the students-per-generation limit and the daily generation count.
    A null limit means unlimited.
    """
    plan = org_plan(org)

    # Students-per-generation check
    if plan.students_per_generation_limit is not None:
        if n_students > plan.students_per_generation_limit:
            return False

    # Daily generation count check
    if plan.generations_per_day_limit is not None:
        if generations_today(org) >= plan.generations_per_day_limit:
            return False

    return True


# ---------------------------------------------------------------------------
# Scan gates
# ---------------------------------------------------------------------------


def scans_this_month(org) -> int:
    """Number of ScanEvents recorded for *org* in the current calendar month (UTC)."""
    now = timezone.now()
    return ScanEvent.objects.filter(
        organization=org,
        created_at__year=now.year,
        created_at__month=now.month,
    ).count()


def can_scan(org) -> bool:
    """True if *org* may process one more scan under its current plan."""
    plan = org_plan(org)
    if plan.monthly_scan_limit is None:
        return True
    return scans_this_month(org) < plan.monthly_scan_limit
