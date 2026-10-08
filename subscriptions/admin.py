from django.contrib import admin
from .models import (
    SubscriptionPlan,
    UserSubscription,
    Payment,
    Invoice,
    SubscriptionHistory,
)


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'price',
        'monthly_application_limit',
        'is_active',
    )


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'plan',
        'status',
        'start_date',
        'end_date',
        'applications_used',
    )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'plan',
        'amount',
        'status',
        'razorpay_order_id',
        'razorpay_payment_id',
        'created_at',
    )


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        'invoice_number',
        'user',
        'plan_name',
        'amount',
        'transaction_id',
        'created_at',
    )


@admin.register(SubscriptionHistory)
class SubscriptionHistoryAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'plan',
        'action',
        'amount',
        'transaction_id',
        'created_at',
    )