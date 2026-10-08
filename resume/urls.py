from django.urls import path
from . import views


urlpatterns = [

    # Create Resume
    path(
        'create/',
        views.create_resume,
        name='create_resume'
    ),

    # Resume OTP
    path(
        'send-otp/',
        views.send_resume_otp,
        name='send_resume_otp'
    ),

    path(
        'verify-otp/',
        views.verify_resume_otp,
        name='verify_resume_otp'
    ),

    # Razorpay Payment
    path(
        'payment/',
        views.resume_payment,
        name='resume_payment'
    ),

    path(
        'payment-success/',
        views.payment_success,
        name='payment_success'
    ),

    # Resume Success
    path(
        'success/',
        views.resume_success,
        name='resume_success'
    ),

    # Download PDF
    path(
        'download/<int:resume_id>/',
        views.download_resume_pdf,
        name='download_resume_pdf'
    ),

    # Set Default Resume
    path(
        'set-default/<int:resume_id>/',
        views.set_default_resume,
        name='set_default_resume'
    ),
]