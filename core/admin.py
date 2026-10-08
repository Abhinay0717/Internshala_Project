from django.contrib import admin

from .models import (
    UserProfile,
    LanguageChangeOTP,
    PasswordResetRequest,
    LoginHistory,
    LoginOTP,
    TrustedDevice,
    ActiveSession,
    LoginVerificationLog,
)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):

    list_display = (
        'user',
        'mobile',
        'must_change_password',
        'language',
    )


@admin.register(LanguageChangeOTP)
class LanguageChangeOTPAdmin(admin.ModelAdmin):

    list_display = (
        'user',
        'otp',
        'created_at',
        'is_verified',
    )


@admin.register(PasswordResetRequest)
class PasswordResetRequestAdmin(admin.ModelAdmin):

    list_display = (
        'user',
        'reset_method',
        'otp_verified',
        'request_time',
        'reset_completed',
    )


@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):

    list_display = (
        'user',
        'status',
        'browser_name',
        'browser_version',
        'operating_system',
        'device_type',
        'ip_address',
        'login_time',
        'otp_required',
        'otp_verified',
        'is_trusted_device',
    )

    list_filter = (
        'status',
        'device_type',
        'otp_required',
        'otp_verified',
        'is_trusted_device',
    )

    search_fields = (
        'user__username',
        'browser_name',
        'ip_address',
        'approximate_location',
    )

    ordering = ('-login_time',)


@admin.register(LoginOTP)
class LoginOTPAdmin(admin.ModelAdmin):

    list_display = (
        'user',
        'otp',
        'created_at',
        'expires_at',
        'verification_attempts',
        'is_verified',
        'is_expired',
    )

    list_filter = (
        'is_verified',
        'is_expired',
    )

    search_fields = (
        'user__username',
    )

    ordering = ('-created_at',)


@admin.register(TrustedDevice)
class TrustedDeviceAdmin(admin.ModelAdmin):

     list_display = (
    'user',
    'browser_name',
    'browser_version',
    'operating_system',
    'device_type',
    'device_model',
    'last_ip_address',
    'is_active',
    'last_used_at',
    )
    
     list_filter = (
        'device_type',
        'is_active',
    )

     search_fields = (
        'user__username',
        'browser_name',
        'device_identifier',
        'last_ip_address',
    )

     ordering = ('-last_used_at',)


@admin.register(ActiveSession)
class ActiveSessionAdmin(admin.ModelAdmin):

    list_display = (
        'user',
        'browser_name',
        'browser_version',
        'operating_system',
        'device_type',
        'ip_address',
        'login_time',
        'last_activity',
        'is_active',
    )

    list_filter = (
        'device_type',
        'is_active',
    )

    search_fields = (
        'user__username',
        'browser_name',
        'ip_address',
        'session_key',
    )

    ordering = ('-last_activity',)


@admin.register(LoginVerificationLog)
class LoginVerificationLogAdmin(admin.ModelAdmin):

    list_display = (
        'user',
        'verification_type',
        'attempt_time',
        'ip_address',
        'browser',
        'device',
    )

    list_filter = (
        'verification_type',
    )

    search_fields = (
        'user__username',
        'ip_address',
        'browser',
        'device',
        'message',
    )

    ordering = ('-attempt_time',)