
from django.db import models
from django.contrib.auth.models import User


# ==========================================================
# USER PROFILE
# ==========================================================

class UserProfile(models.Model):

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    language = models.CharField(
        max_length=10,
        default='en'
    )

    mobile = models.CharField(
        max_length=15,
        blank=True,
        null=True
    )

    must_change_password = models.BooleanField(
        default=False
    )

    def __str__(self):
        return self.user.username


# ==========================================================
# LANGUAGE CHANGE OTP
# ==========================================================

class LanguageChangeOTP(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    otp = models.CharField(
        max_length=6
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    is_verified = models.BooleanField(
        default=False
    )

    def __str__(self):
        return f"{self.user.username} - {self.otp}"


# ==========================================================
# PASSWORD RESET REQUEST
# ==========================================================

class PasswordResetRequest(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    reset_method = models.CharField(
        max_length=10
    )

    otp = models.CharField(
        max_length=6
    )

    otp_created_at = models.DateTimeField(
        auto_now_add=True
    )

    otp_verified = models.BooleanField(
        default=False
    )

    verification_attempts = models.IntegerField(
        default=0
    )

    last_otp_sent_at = models.DateTimeField(
        auto_now_add=True
    )

    request_time = models.DateTimeField(
        auto_now_add=True
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True
    )

    browser = models.TextField(
        blank=True
    )

    device = models.TextField(
        blank=True
    )

    reset_completed = models.BooleanField(
        default=False
    )

    def __str__(self):
        return f"{self.user.username} - {self.reset_method}"


# ==========================================================
# LOGIN HISTORY
# ==========================================================

class LoginHistory(models.Model):

    LOGIN_STATUS_CHOICES = [
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('blocked', 'Blocked'),
        ('otp_required', 'OTP Required'),
        ('otp_failed', 'OTP Failed'),
    ]

    DEVICE_TYPE_CHOICES = [
        ('desktop', 'Desktop'),
        ('laptop', 'Laptop'),
        ('tablet', 'Tablet'),
        ('mobile', 'Mobile'),
        ('unknown', 'Unknown'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='login_history',
        null=True,
        blank=True
    )

    browser_name = models.CharField(
        max_length=100,
        blank=True
    )

    browser_version = models.CharField(
        max_length=100,
        blank=True
    )

    operating_system = models.CharField(
        max_length=150,
        blank=True
    )

    device_type = models.CharField(
        max_length=20,
        choices=DEVICE_TYPE_CHOICES,
        default='unknown'
    )

    device_model = models.CharField(
        max_length=150,
        blank=True
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True
    )

    approximate_location = models.CharField(
        max_length=255,
        blank=True
    )

    login_time = models.DateTimeField(
        auto_now_add=True
    )

    status = models.CharField(
        max_length=20,
        choices=LOGIN_STATUS_CHOICES
    )

    failure_reason = models.CharField(
        max_length=255,
        blank=True
    )

    is_new_browser = models.BooleanField(
        default=False
    )

    is_new_device = models.BooleanField(
        default=False
    )

    is_new_ip = models.BooleanField(
        default=False
    )

    otp_required = models.BooleanField(
        default=False
    )

    otp_verified = models.BooleanField(
        default=False
    )

    is_trusted_device = models.BooleanField(
        default=False
    )

    session_key = models.CharField(
        max_length=255,
        blank=True
     )
    def __str__(self):
        username = self.user.username if self.user else "Unknown User"
        return (
        f"{username} - "
         f"{self.status} - "
         f"{self.login_time}"
    )


# ==========================================================
# LOGIN OTP
# ==========================================================

class LoginOTP(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='login_otps'
    )

    otp = models.CharField(
        max_length=6
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    expires_at = models.DateTimeField()

    verification_attempts = models.IntegerField(
        default=0
    )

    is_verified = models.BooleanField(
        default=False
    )

    is_expired = models.BooleanField(
        default=False
    )

    login_history = models.ForeignKey(
        LoginHistory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='otp_records'
    )

    def __str__(self):
        return f"{self.user.username} - Login OTP"


# ==========================================================
# TRUSTED DEVICES
# ==========================================================

class TrustedDevice(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='trusted_devices'
    )

    browser_name = models.CharField(
        max_length=100,
        blank=True
    )

    browser_version = models.CharField(
        max_length=100,
        blank=True
    )

    operating_system = models.CharField(
        max_length=150,
        blank=True
    )

    device_type = models.CharField(
        max_length=20,
        blank=True
    )

    device_model = models.CharField(
        max_length=150,
        blank=True
    )

    device_identifier = models.CharField(
        max_length=255
    )

    last_ip_address = models.GenericIPAddressField(
        null=True,
        blank=True
    )

    first_trusted_at = models.DateTimeField(
        auto_now_add=True
    )

    last_used_at = models.DateTimeField(
        auto_now=True
    )

    is_active = models.BooleanField(
        default=True
    )

    def __str__(self):
        return (
            f"{self.user.username} - "
            f"{self.device_type} - "
            f"{self.device_identifier}"
        )


# ==========================================================
# ACTIVE SESSIONS
# ==========================================================

class ActiveSession(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='active_sessions'
    )

    session_key = models.CharField(
        max_length=255,
        unique=True
    )

    browser_name = models.CharField(
        max_length=100,
        blank=True
    )

    browser_version = models.CharField(
        max_length=100,
        blank=True
    )

    operating_system = models.CharField(
        max_length=150,
        blank=True
    )

    device_type = models.CharField(
        max_length=20,
        blank=True
    )

    device_model = models.CharField(
        max_length=150,
        blank=True
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True
    )

    login_time = models.DateTimeField(
        auto_now_add=True
    )

    last_activity = models.DateTimeField(
        auto_now=True
    )

    is_active = models.BooleanField(
        default=True
    )

    def __str__(self):
        return (
            f"{self.user.username} - "
            f"{self.device_type} - "
            f"{self.ip_address}"
        )


# ==========================================================
# LOGIN VERIFICATION LOG
# ==========================================================

class LoginVerificationLog(models.Model):

    VERIFICATION_CHOICES = [
        ('otp_sent', 'OTP Sent'),
        ('otp_verified', 'OTP Verified'),
        ('otp_failed', 'OTP Failed'),
        ('otp_expired', 'OTP Expired'),
        ('blocked', 'Blocked'),
        ('success', 'Success'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='login_verification_logs'
    )

    login_history = models.ForeignKey(
        LoginHistory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    verification_type = models.CharField(
        max_length=30,
        choices=VERIFICATION_CHOICES
    )

    attempt_time = models.DateTimeField(
        auto_now_add=True
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True
    )

    browser = models.CharField(
        max_length=150,
        blank=True
    )

    device = models.CharField(
        max_length=150,
        blank=True
    )

    message = models.CharField(
        max_length=255,
        blank=True
    )

    def __str__(self):
        return (
            f"{self.user.username} - "
            f"{self.verification_type}"
        )

