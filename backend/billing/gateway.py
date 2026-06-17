"""
Razorpay gateway abstraction.

All calls to the Razorpay SDK go through this module so that tests can
easily mock at the module boundary (patch 'billing.gateway.create_subscription').
"""

import hashlib
import hmac

import razorpay
from django.conf import settings


def get_client():
    """Return an authenticated razorpay.Client using settings keys."""
    return razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )


def create_subscription(org, plan):
    """Create a Razorpay subscription for *org* on *plan*.

    Returns a dict with at minimum:
        {
            "id":        "<razorpay subscription id>",
            "short_url": "<checkout short URL>",
            "status":    "<razorpay status string>",
        }

    In tests, mock this entire function with unittest.mock.patch so that
    no real HTTP call is made.
    """
    client = get_client()
    result = client.subscription.create(
        {
            "plan_id": plan.razorpay_plan_id,
            "total_count": 12,  # up to 12 billing cycles; adjust as needed
            "quantity": 1,
        }
    )
    return {
        "id": result["id"],
        "short_url": result.get("short_url", ""),
        "status": result.get("status", "created"),
    }


def verify_webhook_signature(raw_body: bytes, signature: str) -> bool:
    """Verify that *signature* is the HMAC-SHA256 of *raw_body* with RAZORPAY_WEBHOOK_SECRET.

    Uses hmac.compare_digest to prevent timing attacks.
    Returns False (not raise) on any mismatch so the caller can return HTTP 400.
    """
    secret = settings.RAZORPAY_WEBHOOK_SECRET.encode()
    expected = hmac.new(secret, raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")
