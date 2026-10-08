from django.db import models
from django.contrib.auth.models import User


class Resume(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    full_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)

    profile_photo = models.ImageField(
        upload_to='resume_photos/',
        blank=True,
        null=True
    )

    career_objective = models.TextField(blank=True)
    education = models.TextField(blank=True)
    skills = models.TextField(blank=True)
    work_experience = models.TextField(blank=True)
    internships = models.TextField(blank=True)
    projects = models.TextField(blank=True)
    certifications = models.TextField(blank=True)
    achievements = models.TextField(blank=True)
    languages = models.TextField(blank=True)
    social_links = models.TextField(blank=True)
    references = models.TextField(blank=True)

    template = models.CharField(
        max_length=50,
        default='template1'
    )

    font = models.CharField(
        max_length=50,
        default='Arial'
    )

    color = models.CharField(
        max_length=50,
        default='black'
    )

    # Default resume for internship applications
    is_default = models.BooleanField(default=False)

    # Payment information
    payment_status = models.CharField(
        max_length=20,
        default='Pending'
    )

    payment_id = models.CharField(
        max_length=100,
        blank=True
    )

    payment_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=50.00
    )

    invoice_number = models.CharField(
        max_length=100,
        blank=True
    )

    # Download information
    download_count = models.PositiveIntegerField(
        default=0
    )

    last_downloaded_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return self.full_name


class ResumeOTP(models.Model):
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


class ResumePayment(models.Model):
    resume = models.ForeignKey(
        Resume,
        on_delete=models.CASCADE,
        related_name='payments'
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    payment_id = models.CharField(
        max_length=100,
        blank=True
    )

    invoice_number = models.CharField(
        max_length=100,
        unique=True
    )

    status = models.CharField(
        max_length=20,
        default='Pending'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.invoice_number


class ResumeDownloadHistory(models.Model):
    resume = models.ForeignKey(
        Resume,
        on_delete=models.CASCADE,
        related_name='downloads'
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    downloaded_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.user.username} - {self.resume.full_name}"


class ResumeVersion(models.Model):
    resume = models.ForeignKey(
        Resume,
        on_delete=models.CASCADE,
        related_name='versions'
    )

    version_number = models.PositiveIntegerField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.resume.full_name} - Version {self.version_number}"