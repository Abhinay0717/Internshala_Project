from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


# =========================================================
# SUBSCRIPTION PLAN
# =========================================================

class SubscriptionPlan(models.Model):

    PLAN_CHOICES = [
        ('free', 'Free'),
        ('bronze', 'Bronze'),
        ('silver', 'Silver'),
        ('gold', 'Gold'),
    ]

    name = models.CharField(
        max_length=20,
        choices=PLAN_CHOICES,
        unique=True
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    monthly_application_limit = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    description = models.TextField(
        blank=True
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.get_name_display()


# =========================================================
# USER SUBSCRIPTION
# =========================================================

class UserSubscription(models.Model):

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('pending', 'Pending'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscriptions'
    )

    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name='user_subscriptions'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    start_date = models.DateTimeField(
        null=True,
        blank=True
    )

    end_date = models.DateTimeField(
        null=True,
        blank=True
    )

    monthly_application_limit = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    applications_used = models.PositiveIntegerField(
        default=0
    )

    # NEW:
    # Stores when the current monthly quota period started.
    quota_start_date = models.DateTimeField(
        null=True,
        blank=True
    )

    # NEW:
    # Stores when the current monthly quota period ends.
    quota_reset_date = models.DateTimeField(
        null=True,
        blank=True
    )

    cancelled_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def remaining_applications(self):

        if self.monthly_application_limit is None:
            return None

        remaining = (
            self.monthly_application_limit
            - self.applications_used
        )

        return max(remaining, 0)

    def is_active(self):

        if self.status != 'active':
            return False

        if self.end_date and timezone.now() >= self.end_date:
            return False

        return True

    def reset_monthly_quota(self):

        """
        Reset the monthly application quota.

        This method resets applications_used to 0
        and moves the quota period forward by one month.

        It does not reset unlimited Gold plans because
        their monthly_application_limit is None.
        """

        if self.monthly_application_limit is None:
            return

        self.applications_used = 0

        now = timezone.now()

        if self.quota_reset_date:
            self.quota_start_date = self.quota_reset_date
            self.quota_reset_date = (
                self.quota_reset_date + timedelta(days=30)
            )
        else:
            self.quota_start_date = now
            self.quota_reset_date = now + timedelta(days=30)

        self.save(
            update_fields=[
                'applications_used',
                'quota_start_date',
                'quota_reset_date',
                'updated_at',
            ]
        )

    def check_and_reset_quota(self):

        """
        Automatically reset the quota when the current
        monthly quota period has ended.
        """

        if not self.is_active():
            return

        if self.monthly_application_limit is None:
            return

        now = timezone.now()

        if (
            self.quota_reset_date
            and now >= self.quota_reset_date
        ):
            self.reset_monthly_quota()

    def renew_period(self):

        """
        Extend the subscription by 30 days.

        Also resets the monthly application quota.
        """

        now = timezone.now()

        if self.end_date and self.end_date > now:
            new_end_date = (
                self.end_date + timedelta(days=30)
            )
        else:
            new_end_date = now + timedelta(days=30)

        self.start_date = (
            self.start_date or now
        )

        self.end_date = new_end_date

        self.status = 'active'

        self.applications_used = 0

        self.quota_start_date = now

        self.quota_reset_date = (
            now + timedelta(days=30)
        )

        self.cancelled_at = None

        self.save()

    def __str__(self):
        return f"{self.user.username} - {self.plan.name}"


# =========================================================
# PAYMENT
# =========================================================

class Payment(models.Model):

    STATUS_CHOICES = [
        ('created', 'Created'),
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('verification_failed', 'Verification Failed'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscription_payments'
    )

    subscription = models.ForeignKey(
        UserSubscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments'
    )

    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    razorpay_order_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True
    )

    razorpay_payment_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True
    )

    razorpay_signature = models.CharField(
        max_length=500,
        blank=True
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='created'
    )

    failure_reason = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    verified_at = models.DateTimeField(
        null=True,
        blank=True
    )

    def __str__(self):
        return (
            f"{self.user.username} - "
            f"{self.plan.name} - "
            f"{self.status}"
        )


# =========================================================
# INVOICE
# =========================================================

class Invoice(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscription_invoices'
    )

    payment = models.OneToOneField(
        Payment,
        on_delete=models.CASCADE,
        related_name='invoice'
    )

    invoice_number = models.CharField(
        max_length=100,
        unique=True
    )

    transaction_id = models.CharField(
        max_length=255
    )

    plan_name = models.CharField(
        max_length=50
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    billing_name = models.CharField(
        max_length=255
    )

    billing_email = models.EmailField()

    billing_phone = models.CharField(
        max_length=30,
        blank=True
    )

    billing_address = models.TextField(
        blank=True
    )

    subscription_start = models.DateTimeField()

    subscription_end = models.DateTimeField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.invoice_number


# =========================================================
# SUBSCRIPTION HISTORY
# =========================================================

class SubscriptionHistory(models.Model):

    ACTION_CHOICES = [
        ('purchase', 'Purchase'),
        ('upgrade', 'Upgrade'),
        ('downgrade', 'Downgrade'),
        ('renew', 'Renew'),
        ('cancel', 'Cancel'),
        ('expire', 'Expire'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscription_history'
    )

    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT
    )

    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    transaction_id = models.CharField(
        max_length=255,
        blank=True
    )

    start_date = models.DateTimeField(
        null=True,
        blank=True
    )

    end_date = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    notes = models.TextField(
        blank=True
    )

    def __str__(self):
        return (
            f"{self.user.username} - "
            f"{self.action} - "
            f"{self.plan.name}"
        )


# =========================================================
# INTERNSHIP APPLICATION
# =========================================================

class InternshipApplication(models.Model):

    STATUS_CHOICES = [
        ('applied', 'Applied'),
        ('under_review', 'Under Review'),
        ('selected', 'Selected'),
        ('rejected', 'Rejected'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='internship_applications'
    )

    internship_title = models.CharField(
        max_length=200
    )

    company_name = models.CharField(
        max_length=200
    )

    application_date = models.DateTimeField(
        auto_now_add=True
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='applied'
    )

    def __str__(self):
        return (
            f"{self.user.username} - "
            f"{self.internship_title}"
        )