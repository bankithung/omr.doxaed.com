"""
Phase 7, Task 2: Billing views — subscribe endpoint + Razorpay webhook.
"""

import json
import logging
from datetime import timezone as dt_timezone

from django.conf import settings
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from organizations.models import Organization, OrganizationMembership
from organizations.views import require_membership

from . import gateway
from .models import Plan, Subscription

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Subscribe endpoint
# ---------------------------------------------------------------------------


class SubscribeView(APIView):
    """
    POST /api/v1/billing/organizations/{id}/subscribe/
    Body: {"plan_code": "<free|team|business|enterprise>"}

    Org ADMIN only. Calls the Razorpay gateway (mocked in tests) to create a
    subscription, then persists a Subscription row (status=created).

    Returns:
        201 {subscription_id, short_url, key_id}
    Errors:
        400 — unknown plan_code
        403 — not an active admin
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, org_id):
        # Require active admin membership (raises 403/404 as appropriate).
        membership = require_membership(
            request, org_id, role=OrganizationMembership.ADMIN
        )
        org = membership.organization

        plan_code = request.data.get("plan_code", "")
        try:
            plan = Plan.objects.get(code=plan_code)
        except Plan.DoesNotExist:
            return Response(
                {"detail": f"Unknown plan_code: '{plan_code}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Call gateway (mocked in tests via patch('billing.gateway.create_subscription')).
        result = gateway.create_subscription(org, plan)

        # Create or update the org's Subscription.
        sub, _created = Subscription.objects.update_or_create(
            organization=org,
            defaults={
                "plan": plan,
                "status": Subscription.CREATED,
                "razorpay_subscription_id": result["id"],
            },
        )

        return Response(
            {
                "subscription_id": sub.razorpay_subscription_id,
                "short_url": result.get("short_url", ""),
                "key_id": settings.RAZORPAY_KEY_ID,
            },
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# Webhook endpoint
# ---------------------------------------------------------------------------


@method_decorator(csrf_exempt, name="dispatch")
class WebhookView(APIView):
    """
    POST /api/v1/billing/webhook/
    AllowAny — Razorpay calls this server-to-server; no user auth.

    Security: the raw body is HMAC-SHA256 verified against X-Razorpay-Signature
    before any processing.  An invalid signature → 400 immediately.

    Supported events (idempotent):
        subscription.activated  → status = active (+ current_period_end)
        subscription.charged    → status = active (+ current_period_end)
        subscription.cancelled  → status = canceled
        subscription.halted     → status = past_due
    """

    authentication_classes = []  # no JWT / session needed
    permission_classes = [AllowAny]

    def post(self, request):
        # Read the raw body BEFORE DRF's JSON parser touches it.
        raw_body = request.body
        signature = request.META.get("HTTP_X_RAZORPAY_SIGNATURE", "")

        if not gateway.verify_webhook_signature(raw_body, signature):
            logger.warning("Razorpay webhook: invalid signature received.")
            return Response(
                {"detail": "Invalid signature."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError:
            return Response(
                {"detail": "Invalid JSON body."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        event = payload.get("event", "")
        subscription_data = (
            payload.get("payload", {})
            .get("subscription", {})
            .get("entity", {})
        )
        razorpay_sub_id = subscription_data.get("id", "")

        if not razorpay_sub_id:
            # Nothing we can act on; ack anyway.
            return Response({"detail": "ok"}, status=status.HTTP_200_OK)

        # Look up our Subscription by the Razorpay subscription ID.
        try:
            sub = Subscription.objects.get(razorpay_subscription_id=razorpay_sub_id)
        except Subscription.DoesNotExist:
            logger.info(
                "Razorpay webhook: no Subscription found for id=%s (event=%s); ignoring.",
                razorpay_sub_id,
                event,
            )
            return Response({"detail": "ok"}, status=status.HTTP_200_OK)

        # Parse current_period_end from the payload when present.
        current_period_end = None
        raw_end = subscription_data.get("current_end")
        if raw_end:
            try:
                from datetime import datetime as _dt
                current_period_end = _dt.fromtimestamp(
                    int(raw_end), tz=dt_timezone.utc
                )
            except (ValueError, TypeError):
                pass

        if event in ("subscription.activated", "subscription.charged"):
            sub.status = Subscription.ACTIVE
            if current_period_end:
                sub.current_period_end = current_period_end
            sub.save(update_fields=["status", "current_period_end", "updated_at"])

        elif event == "subscription.cancelled":
            sub.status = Subscription.CANCELED
            sub.save(update_fields=["status", "updated_at"])

        elif event == "subscription.halted":
            sub.status = Subscription.PAST_DUE
            sub.save(update_fields=["status", "updated_at"])

        # Unknown events are acknowledged but ignored (idempotent).
        return Response({"detail": "ok"}, status=status.HTTP_200_OK)
