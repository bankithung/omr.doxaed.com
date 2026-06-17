from django.db import models


class Plan(models.Model):
    """Seeded plan tiers: free | team | business | enterprise."""

    FREE = "free"
    TEAM = "team"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"
    CODE_CHOICES = [
        (FREE, "Free"),
        (TEAM, "Team"),
        (BUSINESS, "Business"),
        (ENTERPRISE, "Enterprise"),
    ]

    code = models.CharField(max_length=32, unique=True, choices=CODE_CHOICES)
    name = models.CharField(max_length=64)
    price_inr = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # null = unlimited
    seat_limit = models.PositiveIntegerField(null=True, blank=True)
    students_per_generation_limit = models.PositiveIntegerField(null=True, blank=True)
    generations_per_day_limit = models.PositiveIntegerField(null=True, blank=True)
    monthly_scan_limit = models.PositiveIntegerField(null=True, blank=True)

    razorpay_plan_id = models.CharField(max_length=128, blank=True, default="")

    class Meta:
        ordering = ["price_inr", "code"]

    def __str__(self):
        return f"{self.name} (INR {self.price_inr})"


class Subscription(models.Model):
    """One active subscription per organization (OneToOne)."""

    CREATED = "created"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    STATUS_CHOICES = [
        (CREATED, "Created"),
        (ACTIVE, "Active"),
        (PAST_DUE, "Past Due"),
        (CANCELED, "Canceled"),
    ]

    organization = models.OneToOneField(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="subscription",
    )
    plan = models.ForeignKey(
        Plan,
        on_delete=models.PROTECT,
        related_name="subscriptions",
    )
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default=CREATED,
    )
    razorpay_subscription_id = models.CharField(max_length=128, blank=True, default="")
    current_period_end = models.DateTimeField(null=True, blank=True)
    seats_purchased = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Subscription org={self.organization_id} plan={self.plan.code} status={self.status}"
