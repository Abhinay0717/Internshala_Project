from django.urls import path
from . import views


urlpatterns = [

    # Subscription plans
    path(
        '',
        views.subscription_plans,
        name='subscription_plans'
    ),

    # Subscription dashboard
    path(
        'dashboard/',
        views.subscription_dashboard,
        name='subscription_dashboard'
    ),

    # Select / purchase / upgrade / downgrade
    path(
        'select/<int:plan_id>/',
        views.select_plan,
        name='select_plan'
    ),

    # Renew subscription
    path(
        'renew/',
        views.renew_subscription,
        name='renew_subscription'
    ),

    # Verify successful Razorpay payment
    path(
        'verify-payment/',
        views.verify_payment,
        name='verify_payment'
    ),

    # Handle failed/cancelled Razorpay payment
    path(
        'payment-failed/',
        views.payment_failed,
        name='payment_failed'
    ),

    # Internship application
    path(
        'apply/',
        views.apply_internship,
        name='apply_internship'
    ),

    # Cancel subscription
    path(
        'cancel/',
        views.cancel_subscription,
        name='cancel_subscription'
    ),

    # Subscription history
    path(
        'history/',
        views.subscription_history,
        name='subscription_history'
    ),
]