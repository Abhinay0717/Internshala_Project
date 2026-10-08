from datetime import time, timedelta
from zoneinfo import ZoneInfo

import razorpay

from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db import transaction

from .models import (
    SubscriptionPlan,
    Payment,
    UserSubscription,
    SubscriptionHistory,
    Invoice,
    InternshipApplication,
)


# =========================================================
# HELPER - CHECK EXPIRY AND RESET MONTHLY QUOTA
# =========================================================

def get_current_subscription(user):
    """
    Get the user's latest active subscription.

    Also:
    1. Marks expired subscriptions as expired.
    2. Creates expiry history.
    3. Resets monthly application quota when required.
    """

    subscription = (
        UserSubscription.objects
        .filter(
            user=user,
            status='active'
        )
        .order_by('-end_date', '-id')
        .first()
    )

    if not subscription:
        return None

    now = timezone.now()

    # =====================================================
    # CHECK SUBSCRIPTION EXPIRY
    # =====================================================

    if (
        subscription.end_date
        and now >= subscription.end_date
    ):

        subscription.status = 'expired'

        subscription.save(
            update_fields=[
                'status',
                'updated_at',
            ]
        )

        SubscriptionHistory.objects.create(
            user=user,
            plan=subscription.plan,
            action='expire',
            amount=0,
            transaction_id='EXPIRED',
            start_date=subscription.start_date,
            end_date=subscription.end_date,
            notes='Subscription expired automatically.'
        )

        return None

    # =====================================================
    # CHECK MONTHLY QUOTA RESET
    # =====================================================

    subscription.check_and_reset_quota()

    subscription.refresh_from_db()

    return subscription


# =========================================================
# SUBSCRIPTION PLANS
# =========================================================

def subscription_plans(request):

    plans = (
        SubscriptionPlan.objects
        .filter(is_active=True)
        .order_by('price')
    )

    return render(
        request,
        'subscriptions/plans.html',
        {
            'plans': plans
        }
    )


# =========================================================
# SELECT / PURCHASE / UPGRADE / DOWNGRADE PLAN
# =========================================================

@login_required
def select_plan(request, plan_id):

    plan = get_object_or_404(
        SubscriptionPlan,
        id=plan_id,
        is_active=True
    )

    current_subscription = get_current_subscription(
        request.user
    )

    # =====================================================
    # FREE PLAN
    # =====================================================

    if plan.name == 'free':

        if (
            current_subscription
            and
            current_subscription.plan.name == 'free'
            and
            current_subscription.is_active()
        ):

            messages.info(
                request,
                'You are already using the Free plan.'
            )

            return redirect(
                'subscription_dashboard'
            )

        # -------------------------------------------------
        # Change existing paid plan to Free
        # -------------------------------------------------

        if (
            current_subscription
            and
            current_subscription.is_active()
        ):

            old_plan = current_subscription.plan

            current_subscription.status = 'cancelled'

            current_subscription.cancelled_at = (
                timezone.now()
            )

            current_subscription.save(
                update_fields=[
                    'status',
                    'cancelled_at',
                    'updated_at',
                ]
            )

            SubscriptionHistory.objects.create(
                user=request.user,
                plan=old_plan,
                action='downgrade',
                amount=0,
                transaction_id='PLAN_CHANGE',
                start_date=current_subscription.start_date,
                end_date=current_subscription.end_date,
                notes=(
                    f'Downgraded from '
                    f'{old_plan.get_name_display()} '
                    f'to Free plan.'
                )
            )

        # -------------------------------------------------
        # Create Free subscription
        # -------------------------------------------------

        start_date = timezone.now()

        end_date = (
            start_date + timedelta(days=30)
        )

        UserSubscription.objects.create(
            user=request.user,
            plan=plan,
            status='active',
            start_date=start_date,
            end_date=end_date,
            monthly_application_limit=(
                plan.monthly_application_limit
            ),
            applications_used=0,
            quota_start_date=start_date,
            quota_reset_date=end_date,
        )

        SubscriptionHistory.objects.create(
            user=request.user,
            plan=plan,
            action='purchase',
            amount=0,
            transaction_id='FREE_PLAN',
            start_date=start_date,
            end_date=end_date,
            notes='Free plan activated.'
        )

        messages.success(
            request,
            'Free plan activated successfully.'
        )

        return redirect(
            'subscription_dashboard'
        )

    # =====================================================
    # SAME ACTIVE PLAN
    # =====================================================

    if (
        current_subscription
        and
        current_subscription.is_active()
        and
        current_subscription.plan.id == plan.id
    ):

        messages.info(
            request,
            'You are already subscribed to this plan. '
            'Use the Renew option to extend your subscription.'
        )

        return redirect(
            'subscription_dashboard'
        )

    # =====================================================
    # DETERMINE PURCHASE / UPGRADE / DOWNGRADE
    # =====================================================

    subscription_action = 'purchase'

    if (
        current_subscription
        and
        current_subscription.is_active()
    ):

        if plan.price > current_subscription.plan.price:

            subscription_action = 'upgrade'

        elif plan.price < current_subscription.plan.price:

            subscription_action = 'downgrade'

    # =====================================================
    # PAYMENT TIME RESTRICTION
    # =====================================================

    india_timezone = ZoneInfo('Asia/Kolkata')

    current_time = (
        timezone.now()
        .astimezone(india_timezone)
        .time()
    )

    payment_start = time(5, 0)
    payment_end = time(11, 45)

    payment_time_allowed = (
        payment_start
        <= current_time
        <= payment_end
    )

    allow_testing = getattr(
        settings,
        'ALLOW_SUBSCRIPTION_PAYMENT_ANYTIME',
        False
    )

    if (
        not payment_time_allowed
        and
        not allow_testing
    ):

        return render(
            request,
            'subscriptions/payment_unavailable.html',
            {
                'plan': plan,
                'current_time': current_time,
            }
        )

    # =====================================================
    # CREATE RAZORPAY ORDER
    # =====================================================

    if request.method == 'POST':

        amount_in_paise = int(
            plan.price * 100
        )

        client = razorpay.Client(
            auth=(
                settings.RAZORPAY_KEY_ID,
                settings.RAZORPAY_KEY_SECRET
            )
        )

        receipt = (
            f'sub_{request.user.id}_'
            f'{plan.id}_'
            f'{timezone.now().strftime("%Y%m%d%H%M%S%f")}'
        )

        order_data = {
            'amount': amount_in_paise,
            'currency': 'INR',
            'receipt': receipt,
        }

        try:

            razorpay_order = client.order.create(
                data=order_data
            )

        except Exception:

            messages.error(
                request,
                'Unable to create the Razorpay payment order. '
                'Please try again later.'
            )

            return redirect(
                'subscription_plans'
            )

        payment = Payment.objects.create(
            user=request.user,
            plan=plan,
            amount=plan.price,
            razorpay_order_id=(
                razorpay_order['id']
            ),
            status='created',
        )

        return render(
            request,
            'subscriptions/razorpay_checkout.html',
            {
                'plan': plan,
                'razorpay_order_id': (
                    razorpay_order['id']
                ),
                'razorpay_key_id': (
                    settings.RAZORPAY_KEY_ID
                ),
                'amount': amount_in_paise,
                'payment': payment,
                'subscription_action': (
                    subscription_action
                ),
            }
        )

    # =====================================================
    # GET REQUEST
    # =====================================================

    return render(
        request,
        'subscriptions/payment.html',
        {
            'plan': plan,
            'subscription_action': (
                subscription_action
            ),
            'current_subscription': (
                current_subscription
            ),
        }
    )


# =========================================================
# RENEW SUBSCRIPTION
# =========================================================

@login_required
def renew_subscription(request):

    current_subscription = get_current_subscription(
        request.user
    )

    if not current_subscription:

        messages.error(
            request,
            'You do not have an active subscription to renew.'
        )

        return redirect(
            'subscription_plans'
        )

    plan = current_subscription.plan

    # =====================================================
    # PAYMENT TIME RESTRICTION
    # =====================================================

    india_timezone = ZoneInfo('Asia/Kolkata')

    current_time = (
        timezone.now()
        .astimezone(india_timezone)
        .time()
    )

    payment_start = time(5, 0)
    payment_end = time(11, 45)

    payment_time_allowed = (
        payment_start
        <= current_time
        <= payment_end
    )

    allow_testing = getattr(
        settings,
        'ALLOW_SUBSCRIPTION_PAYMENT_ANYTIME',
        False
    )

    if (
        not payment_time_allowed
        and
        not allow_testing
    ):

        return render(
            request,
            'subscriptions/payment_unavailable.html',
            {
                'plan': plan,
                'current_time': current_time,
            }
        )

    # =====================================================
    # CREATE RENEWAL PAYMENT
    # =====================================================

    if request.method == 'POST':

        amount_in_paise = int(
            plan.price * 100
        )

        client = razorpay.Client(
            auth=(
                settings.RAZORPAY_KEY_ID,
                settings.RAZORPAY_KEY_SECRET
            )
        )

        receipt = (
            f'renew_{request.user.id}_'
            f'{plan.id}_'
            f'{timezone.now().strftime("%Y%m%d%H%M%S%f")}'
        )

        order_data = {
            'amount': amount_in_paise,
            'currency': 'INR',
            'receipt': receipt,
        }

        try:

            razorpay_order = client.order.create(
                data=order_data
            )

        except Exception:

            messages.error(
                request,
                'Unable to create the Razorpay renewal order. '
                'Please try again later.'
            )

            return redirect(
                'subscription_dashboard'
            )

        payment = Payment.objects.create(
            user=request.user,
            plan=plan,
            amount=plan.price,
            razorpay_order_id=(
                razorpay_order['id']
            ),
            status='created',
        )

        return render(
            request,
            'subscriptions/razorpay_checkout.html',
            {
                'plan': plan,
                'razorpay_order_id': (
                    razorpay_order['id']
                ),
                'razorpay_key_id': (
                    settings.RAZORPAY_KEY_ID
                ),
                'amount': amount_in_paise,
                'payment': payment,
                'subscription_action': 'renew',
            }
        )

    return render(
        request,
        'subscriptions/payment.html',
        {
            'plan': plan,
            'subscription_action': 'renew',
            'current_subscription': (
                current_subscription
            ),
        }
    )


# =========================================================
# PAYMENT FAILED / CANCELLED
# =========================================================

@login_required
def payment_failed(request):

    if request.method != 'POST':

        return redirect(
            'subscription_plans'
        )

    order_id = request.POST.get(
        'razorpay_order_id'
    )

    payment_id = request.POST.get(
        'razorpay_payment_id'
    )

    reason = (
        request.POST.get('reason')
        or
        'Razorpay payment failed or was cancelled.'
    )

    if not order_id:

        messages.error(
            request,
            'Payment order information is missing.'
        )

        return redirect(
            'subscription_plans'
        )

    try:

        payment = Payment.objects.get(
            razorpay_order_id=order_id,
            user=request.user
        )

    except Payment.DoesNotExist:

        messages.error(
            request,
            'Payment record could not be found.'
        )

        return redirect(
            'subscription_plans'
        )

    # =====================================================
    # NEVER CHANGE SUCCESSFUL PAYMENT
    # =====================================================

    if payment.status == 'success':

        messages.info(
            request,
            'This payment was already completed successfully.'
        )

        return redirect(
            'subscription_dashboard'
        )

    # =====================================================
    # PREVENT DUPLICATE FAILURE PROCESSING
    # =====================================================

    if payment.status in [
        'failed',
        'cancelled',
        'verification_failed',
    ]:

        messages.info(
            request,
            'This payment has already been processed.'
        )

        return redirect(
            'subscription_dashboard'
        )

    # =====================================================
    # DETERMINE FAILED OR CANCELLED
    # =====================================================

    reason_lower = reason.lower()

    if (
        'closed by the user' in reason_lower
        or
        'cancelled' in reason_lower
        or
        'canceled' in reason_lower
        or
        'window was closed' in reason_lower
    ):

        payment.status = 'cancelled'

    else:

        payment.status = 'failed'

    # =====================================================
    # SAVE PAYMENT ID IF AVAILABLE
    # =====================================================

    if payment_id:
        payment.razorpay_payment_id = payment_id

    payment.failure_reason = reason

    update_fields = [
        'status',
        'failure_reason',
    ]

    if payment_id:
        update_fields.append(
            'razorpay_payment_id'
        )

    payment.save(
        update_fields=update_fields
    )

    # =====================================================
    # MESSAGE
    # =====================================================

    if payment.status == 'cancelled':

        messages.warning(
            request,
            'Payment was cancelled. '
            'Your subscription was not changed.'
        )

    else:

        messages.error(
            request,
            'Payment failed. '
            'Your subscription was not changed.'
        )

    return redirect(
        'subscription_dashboard'
    )


# =========================================================
# VERIFY RAZORPAY PAYMENT
# =========================================================

@login_required
def verify_payment(request):

    if request.method != 'POST':

        return redirect(
            'subscription_plans'
        )

    payment_id = request.POST.get(
        'razorpay_payment_id'
    )

    order_id = request.POST.get(
        'razorpay_order_id'
    )

    signature = request.POST.get(
        'razorpay_signature'
    )

    # =====================================================
    # CHECK PAYMENT INFORMATION
    # =====================================================

    if (
        not payment_id
        or
        not order_id
        or
        not signature
    ):

        messages.error(
            request,
            'Payment verification information is missing.'
        )

        return redirect(
            'subscription_plans'
        )

    # =====================================================
    # FIND PAYMENT
    # =====================================================

    payment = get_object_or_404(
        Payment,
        razorpay_order_id=order_id,
        user=request.user
    )

    # =====================================================
    # CHECK DUPLICATE RAZORPAY PAYMENT ID
    # =====================================================

    duplicate_payment = (
        Payment.objects
        .filter(
            razorpay_payment_id=payment_id,
            status='success'
        )
        .exclude(
            id=payment.id
        )
        .first()
    )

    if duplicate_payment:

        messages.error(
            request,
            'This Razorpay payment has already been used.'
        )

        return redirect(
            'subscription_dashboard'
        )

    # =====================================================
    # PREVENT DUPLICATE VERIFICATION
    # =====================================================

    if payment.status == 'success':

        messages.info(
            request,
            'This payment has already been verified.'
        )

        return redirect(
            'subscription_dashboard'
        )

    # =====================================================
    # DO NOT VERIFY FAILED/CANCELLED PAYMENT
    # =====================================================

    if payment.status in [
        'failed',
        'cancelled',
        'verification_failed',
    ]:

        messages.error(
            request,
            'This payment cannot be verified because '
            'it has already been marked as failed or cancelled.'
        )

        return redirect(
            'subscription_dashboard'
        )

    # =====================================================
    # RAZORPAY CLIENT
    # =====================================================

    client = razorpay.Client(
        auth=(
            settings.RAZORPAY_KEY_ID,
            settings.RAZORPAY_KEY_SECRET
        )
    )

    # =====================================================
    # VERIFY SIGNATURE
    # =====================================================

    try:

        client.utility.verify_payment_signature(
            {
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature,
            }
        )

    except razorpay.errors.SignatureVerificationError:

        payment.status = 'verification_failed'

        payment.failure_reason = (
            'Invalid Razorpay signature.'
        )

        payment.save(
            update_fields=[
                'status',
                'failure_reason',
            ]
        )

        messages.error(
            request,
            'Payment verification failed because '
            'the payment signature is invalid.'
        )

        return redirect(
            'subscription_plans'
        )

    except Exception:

        payment.status = 'verification_failed'

        payment.failure_reason = (
            'Unexpected error during payment verification.'
        )

        payment.save(
            update_fields=[
                'status',
                'failure_reason',
            ]
        )

        messages.error(
            request,
            'Payment verification could not be completed.'
        )

        return redirect(
            'subscription_plans'
        )

    # =====================================================
    # VERIFY PAYMENT WITH RAZORPAY
    # =====================================================

    try:

        razorpay_payment = client.payment.fetch(
            payment_id
        )

        razorpay_order_id = (
            razorpay_payment.get('order_id')
        )

        razorpay_status = (
            razorpay_payment.get('status')
        )

        if razorpay_order_id != order_id:

            payment.status = (
                'verification_failed'
            )

            payment.failure_reason = (
                'Payment does not belong to the supplied order.'
            )

            payment.save(
                update_fields=[
                    'status',
                    'failure_reason',
                ]
            )

            messages.error(
                request,
                'Payment verification failed because '
                'the payment order does not match.'
            )

            return redirect(
                'subscription_plans'
            )

        if razorpay_status != 'captured':

            payment.status = (
                'verification_failed'
            )

            payment.failure_reason = (
                f'Razorpay payment status was '
                f'{razorpay_status}.'
            )

            payment.save(
                update_fields=[
                    'status',
                    'failure_reason',
                ]
            )

            messages.error(
                request,
                'Payment has not been successfully captured.'
            )

            return redirect(
                'subscription_plans'
            )

    except Exception:

        payment.status = (
            'verification_failed'
        )

        payment.failure_reason = (
            'Unable to confirm payment status with Razorpay.'
        )

        payment.save(
            update_fields=[
                'status',
                'failure_reason',
            ]
        )

        messages.error(
            request,
            'Unable to confirm the payment with Razorpay.'
        )

        return redirect(
            'subscription_plans'
        )

    # =====================================================
    # PROCESS SUCCESSFUL PAYMENT SAFELY
    # =====================================================

    with transaction.atomic():

        payment = (
            Payment.objects
            .select_for_update()
            .select_related('plan')
            .get(
                id=payment.id
            )
        )

        # =================================================
        # SECOND DUPLICATE CHECK
        # =================================================

        if payment.status == 'success':

            messages.info(
                request,
                'This payment has already been processed.'
            )

            return redirect(
                'subscription_dashboard'
            )

        # =================================================
        # CHECK PAYMENT ID AGAIN INSIDE TRANSACTION
        # =================================================

        duplicate_payment = (
            Payment.objects
            .select_for_update()
            .filter(
                razorpay_payment_id=payment_id,
                status='success'
            )
            .exclude(
                id=payment.id
            )
            .first()
        )

        if duplicate_payment:

            messages.error(
                request,
                'This Razorpay payment has already been used.'
            )

            return redirect(
                'subscription_dashboard'
            )

        # =================================================
        # SAVE PAYMENT SUCCESS
        # =================================================

        payment.razorpay_payment_id = (
            payment_id
        )

        payment.razorpay_signature = (
            signature
        )

        payment.status = 'success'

        payment.verified_at = timezone.now()

        payment.save()

        # =================================================
        # GET CURRENT SUBSCRIPTION
        # =================================================

        current_subscription = get_current_subscription(
            request.user
        )

        # =================================================
        # DETERMINE ACTION
        # =================================================

        subscription_action = 'purchase'

        if current_subscription:

            if (
                payment.plan.id
                ==
                current_subscription.plan.id
            ):

                subscription_action = 'renew'

            elif (
                payment.plan.price
                >
                current_subscription.plan.price
            ):

                subscription_action = 'upgrade'

            elif (
                payment.plan.price
                <
                current_subscription.plan.price
            ):

                subscription_action = 'downgrade'

        # =================================================
        # RENEW EXISTING SAME PLAN
        # =================================================

        if (
            subscription_action == 'renew'
            and
            current_subscription
        ):

            current_subscription.renew_period()

            subscription = current_subscription

            start_date = subscription.start_date

            end_date = subscription.end_date

        else:

            # =============================================
            # CLOSE OLD ACTIVE SUBSCRIPTION
            # =============================================

            if (
                current_subscription
                and
                current_subscription.is_active()
            ):

                current_subscription.status = 'cancelled'

                current_subscription.cancelled_at = (
                    timezone.now()
                )

                current_subscription.save(
                    update_fields=[
                        'status',
                        'cancelled_at',
                        'updated_at',
                    ]
                )

            # =============================================
            # CREATE NEW SUBSCRIPTION
            # =============================================

            start_date = timezone.now()

            end_date = (
                start_date + timedelta(days=30)
            )

            subscription = (
                UserSubscription.objects.create(
                    user=request.user,
                    plan=payment.plan,
                    status='active',
                    start_date=start_date,
                    end_date=end_date,
                    monthly_application_limit=(
                        payment.plan.monthly_application_limit
                    ),
                    applications_used=0,
                    quota_start_date=start_date,
                    quota_reset_date=end_date,
                )
            )

        # =================================================
        # CONNECT PAYMENT TO SUBSCRIPTION
        # =================================================

        payment.subscription = subscription

        payment.save(
            update_fields=[
                'subscription'
            ]
        )

        # =================================================
        # SAVE SUBSCRIPTION HISTORY
        # =================================================

        SubscriptionHistory.objects.create(
            user=request.user,
            plan=payment.plan,
            action=subscription_action,
            amount=payment.amount,
            transaction_id=payment_id,
            start_date=start_date,
            end_date=end_date,
            notes=(
                f'Subscription {subscription_action} '
                f'through Razorpay.'
            )
        )

        # =================================================
        # CREATE INVOICE ONLY IF NOT ALREADY CREATED
        # =================================================

        invoice = Invoice.objects.filter(
            payment=payment
        ).first()

        if not invoice:

            invoice_number = (
                f'INV-'
                f'{timezone.now().strftime("%Y%m%d%H%M%S%f")}'
                f'-{request.user.id}'
            )

            invoice = Invoice.objects.create(
                user=request.user,
                payment=payment,
                invoice_number=invoice_number,
                transaction_id=payment_id,
                plan_name=(
                    payment.plan.get_name_display()
                ),
                amount=payment.amount,
                billing_name=(
                    request.user.get_full_name()
                    or
                    request.user.username
                ),
                billing_email=request.user.email,
                billing_phone='',
                billing_address='',
                subscription_start=start_date,
                subscription_end=end_date,
            )

        else:

            invoice_number = invoice.invoice_number

    # =====================================================
    # SEND CONFIRMATION EMAIL
    # =====================================================

    if request.user.email:

        send_mail(
            subject='Subscription Payment Successful',
            message=(
                f'Hello '
                f'{request.user.get_full_name() or request.user.username},\n\n'

                f'Your subscription payment was successful.\n\n'

                f'Plan: '
                f'{payment.plan.get_name_display()}\n'

                f'Amount: ₹{payment.amount}\n'

                f'Transaction ID: '
                f'{payment_id}\n'

                f'Invoice Number: '
                f'{invoice_number}\n'

                f'Subscription Start: '
                f'{start_date}\n'

                f'Subscription End: '
                f'{end_date}\n\n'

                f'Thank you for using '
                f'Internshala Internship Portal.'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[
                request.user.email
            ],
            fail_silently=True,
        )

    # =====================================================
    # SUCCESS MESSAGE
    # =====================================================

    if subscription_action == 'upgrade':

        success_message = (
            'Payment successful! '
            'Your subscription has been upgraded.'
        )

    elif subscription_action == 'downgrade':

        success_message = (
            'Payment successful! '
            'Your subscription has been changed '
            'to the selected plan.'
        )

    elif subscription_action == 'renew':

        success_message = (
            'Payment successful! '
            'Your subscription has been renewed '
            'and your monthly application quota '
            'has been reset.'
        )

    else:

        success_message = (
            'Payment successful! '
            'Your subscription is now active.'
        )

    messages.success(
        request,
        success_message
    )

    return redirect(
        'subscription_dashboard'
    )


# =========================================================
# SUBSCRIPTION DASHBOARD
# =========================================================

@login_required
def subscription_dashboard(request):

    subscription = get_current_subscription(
        request.user
    )

    payments = (
        Payment.objects
        .filter(
            user=request.user
        )
        .order_by('-created_at')
    )

    invoices = (
        Invoice.objects
        .filter(
            user=request.user
        )
        .order_by('-created_at')
    )

    return render(
        request,
        'subscriptions/dashboard.html',
        {
            'subscription': subscription,
            'payments': payments,
            'invoices': invoices,
        }
    )


# =========================================================
# INTERNSHIP APPLICATION
# =========================================================

@login_required
def apply_internship(request):

    # =====================================================
    # HANDLE POST WITH DATABASE LOCK
    # =====================================================

    if request.method == 'POST':

        internship_title = request.POST.get(
            'internship_title'
        )

        company_name = request.POST.get(
            'company_name'
        )

        if (
            not internship_title
            or
            not company_name
        ):

            messages.error(
                request,
                'Internship title and company '
                'name are required.'
            )

            return redirect(
                'apply_internship'
            )

        # -------------------------------------------------
        # Lock subscription row while checking quota
        # -------------------------------------------------

        with transaction.atomic():

            subscription = (
                UserSubscription.objects
                .select_for_update()
                .select_related('plan')
                .filter(
                    user=request.user,
                    status='active'
                )
                .order_by('-end_date', '-id')
                .first()
            )

            # ---------------------------------------------
            # No active subscription
            # ---------------------------------------------

            if not subscription:

                messages.error(
                    request,
                    'You need an active subscription '
                    'to apply for an internship.'
                )

                return redirect(
                    'subscription_plans'
                )

            # ---------------------------------------------
            # Check expiry while row is locked
            # ---------------------------------------------

            now = timezone.now()

            if (
                subscription.end_date
                and
                now >= subscription.end_date
            ):

                subscription.status = 'expired'

                subscription.save(
                    update_fields=[
                        'status',
                        'updated_at',
                    ]
                )

                SubscriptionHistory.objects.create(
                    user=request.user,
                    plan=subscription.plan,
                    action='expire',
                    amount=0,
                    transaction_id='EXPIRED',
                    start_date=subscription.start_date,
                    end_date=subscription.end_date,
                    notes='Subscription expired automatically.'
                )

                messages.error(
                    request,
                    'Your subscription has expired.'
                )

                return redirect(
                    'subscription_plans'
                )

            # ---------------------------------------------
            # Check and reset quota
            # ---------------------------------------------

            subscription.check_and_reset_quota()

            subscription.refresh_from_db()

            # ---------------------------------------------
            # Check application quota
            # ---------------------------------------------

            if (
                subscription.monthly_application_limit
                is not None
                and
                subscription.applications_used
                >=
                subscription.monthly_application_limit
            ):

                messages.error(
                    request,
                    'You have reached your monthly '
                    'internship application limit.'
                )

                return redirect(
                    'subscription_dashboard'
                )

            # ---------------------------------------------
            # Create application
            # ---------------------------------------------

            InternshipApplication.objects.create(
                user=request.user,
                internship_title=internship_title,
                company_name=company_name,
            )

            # ---------------------------------------------
            # Increase quota usage
            # ---------------------------------------------

            subscription.applications_used += 1

            subscription.save(
                update_fields=[
                    'applications_used',
                    'updated_at',
                ]
            )

        messages.success(
            request,
            'Internship application '
            'submitted successfully.'
        )

        return redirect(
            'subscription_dashboard'
        )

    # =====================================================
    # GET REQUEST
    # =====================================================

    subscription = get_current_subscription(
        request.user
    )

    # =====================================================
    # CHECK ACTIVE SUBSCRIPTION
    # =====================================================

    if (
        not subscription
        or
        not subscription.is_active()
    ):

        messages.error(
            request,
            'You need an active subscription '
            'to apply for an internship.'
        )

        return redirect(
            'subscription_plans'
        )

    # =====================================================
    # CHECK APPLICATION QUOTA
    # =====================================================

    if (
        subscription.monthly_application_limit
        is not None
        and
        subscription.applications_used
        >=
        subscription.monthly_application_limit
    ):

        messages.error(
            request,
            'You have reached your monthly '
            'internship application limit.'
        )

        return redirect(
            'subscription_dashboard'
        )

    return render(
        request,
        'subscriptions/apply_internship.html',
        {
            'subscription': subscription,
        }
    )


# =========================================================
# CANCEL SUBSCRIPTION
# =========================================================

@login_required
def cancel_subscription(request):

    subscription = get_current_subscription(
        request.user
    )

    if (
        not subscription
        or
        not subscription.is_active()
    ):

        messages.error(
            request,
            'You do not have an active '
            'subscription to cancel.'
        )

        return redirect(
            'subscription_dashboard'
        )

    # =====================================================
    # CANCEL SUBSCRIPTION
    # =====================================================

    if request.method == 'POST':

        subscription.status = 'cancelled'

        subscription.cancelled_at = (
            timezone.now()
        )

        subscription.save(
            update_fields=[
                'status',
                'cancelled_at',
                'updated_at',
            ]
        )

        SubscriptionHistory.objects.create(
            user=request.user,
            plan=subscription.plan,
            action='cancel',
            amount=0,
            transaction_id='CANCELLED',
            start_date=subscription.start_date,
            end_date=subscription.end_date,
            notes=(
                'Subscription cancelled '
                'by user.'
            )
        )

        messages.success(
            request,
            'Your subscription has been '
            'cancelled successfully.'
        )

        return redirect(
            'subscription_dashboard'
        )

    return render(
        request,
        'subscriptions/cancel_subscription.html',
        {
            'subscription': subscription,
        }
    )


# =========================================================
# SUBSCRIPTION HISTORY
# =========================================================

@login_required
def subscription_history(request):

    history = (
        SubscriptionHistory.objects
        .filter(
            user=request.user
        )
        .order_by('-created_at')
    )

    return render(
        request,
        'subscriptions/history.html',
        {
            'history': history,
        }
    )