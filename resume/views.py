from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)

from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings

from .forms import ResumeForm, OTPForm
from .models import (
    Resume,
    ResumeOTP,
    ResumePayment,
    ResumeDownloadHistory,
    ResumeVersion
)

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

import razorpay
import random
import uuid

from datetime import timedelta
from django.utils import timezone


# ==========================================
# CREATE RESUME
# ==========================================

@login_required
def create_resume(request):

    if request.method == 'POST':

        form = ResumeForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():

            resume = form.save(commit=False)

            resume.user = request.user

            resume.payment_status = 'Pending'
            resume.payment_amount = 50.00

            resume.save()

            # Store resume ID in session
            request.session['resume_id'] = resume.id

            # Reset previous payment/OTP session values
            request.session.pop(
                'resume_otp_verified',
                None
            )

            request.session.pop(
                'payment_verified',
                None
            )

            request.session.pop(
                'razorpay_order_id',
                None
            )

            # Go to OTP
            return redirect(
                'send_resume_otp'
            )

    else:

        form = ResumeForm()

    return render(
        request,
        'resume/create_resume.html',
        {
            'form': form
        }
    )


# ==========================================
# SEND RESUME OTP
# ==========================================

@login_required
def send_resume_otp(request):

    resume_id = request.session.get(
        'resume_id'
    )

    if not resume_id:

        return redirect(
            'create_resume'
        )

    resume = get_object_or_404(
        Resume,
        id=resume_id,
        user=request.user
    )

    # Check email
    if not request.user.email:

        return render(
            request,
            'resume/verify_otp.html',
            {
                'error': (
                    'Please add a registered email '
                    'address to your account first.'
                )
            }
        )

    # Generate 6 digit OTP
    otp = str(
        random.randint(
            100000,
            999999
        )
    )

    # Invalidate previous OTPs
    ResumeOTP.objects.filter(
        user=request.user,
        is_verified=False
    ).update(
        is_verified=True
    )

    # Create new OTP
    ResumeOTP.objects.create(
        user=request.user,
        otp=otp
    )

    # Send OTP
    send_mail(
        subject='Resume Builder OTP',

        message=(
            f'Your Resume Builder OTP is: {otp}\n\n'
            'This OTP is required before payment.'
        ),

        from_email=settings.DEFAULT_FROM_EMAIL,

        recipient_list=[
            request.user.email
        ],

        fail_silently=False
    )

    return redirect(
        'verify_resume_otp'
    )


# ==========================================
# VERIFY RESUME OTP
# ==========================================

@login_required
def verify_resume_otp(request):

    if request.method == 'POST':

        form = OTPForm(
            request.POST
        )

        if form.is_valid():

            entered_otp = form.cleaned_data[
                'otp'
            ]

            # Find latest valid OTP
            otp_record = ResumeOTP.objects.filter(
                user=request.user,
                otp=entered_otp,
                is_verified=False
            ).order_by(
                '-created_at'
            ).first()

            if otp_record:

                # OTP expires after 5 minutes
                expiry_time = (
                    otp_record.created_at
                    + timedelta(minutes=5)
                )

                if timezone.now() <= expiry_time:

                    # Mark OTP verified
                    otp_record.is_verified = True

                    otp_record.save()

                    # Store verification in session
                    request.session[
                        'resume_otp_verified'
                    ] = True

                    # Continue to payment
                    return redirect(
                        'resume_payment'
                    )

            return render(
                request,
                'resume/verify_otp.html',
                {
                    'form': form,
                    'error': (
                        'Invalid or expired OTP.'
                    )
                }
            )

    else:

        form = OTPForm()

    return render(
        request,
        'resume/verify_otp.html',
        {
            'form': form
        }
    )


# ==========================================
# RAZORPAY PAYMENT
# ==========================================

@login_required
def resume_payment(request):

    # OTP must be verified first
    otp_verified = request.session.get(
        'resume_otp_verified',
        False
    )

    if not otp_verified:

        return redirect(
            'send_resume_otp'
        )

    # Get resume
    resume_id = request.session.get(
        'resume_id'
    )

    if not resume_id:

        return redirect(
            'create_resume'
        )

    resume = get_object_or_404(
        Resume,
        id=resume_id,
        user=request.user
    )

    # If already paid, don't create another order
    if resume.payment_status == 'Paid':

        request.session[
            'payment_verified'
        ] = True

        return redirect(
            'resume_success'
        )

    # Razorpay client
    client = razorpay.Client(
        auth=(
            settings.RAZORPAY_KEY_ID,
            settings.RAZORPAY_KEY_SECRET
        )
    )

    # ₹50 = 5000 paise
    payment_data = {
        'amount': 5000,
        'currency': 'INR',
        'receipt': f'resume_{resume.id}',
    }

    # Create Razorpay order
    order = client.order.create(
        data=payment_data
    )

    # Store order ID
    request.session[
        'razorpay_order_id'
    ] = order['id']

    return render(
        request,
        'resume/payment.html',
        {
            'resume': resume,

            'order': order,

            'razorpay_key_id':
                settings.RAZORPAY_KEY_ID,

            'amount': 5000,
        }
    )


# ==========================================
# PAYMENT SUCCESS / VERIFICATION
# ==========================================

@login_required
def payment_success(request):

    # Support both GET and POST
    payment_id = (
        request.POST.get('razorpay_payment_id')
        or request.POST.get('payment_id')
        or request.GET.get('razorpay_payment_id')
        or request.GET.get('payment_id')
    )

    order_id = (
        request.POST.get('razorpay_order_id')
        or request.POST.get('order_id')
        or request.GET.get('razorpay_order_id')
        or request.GET.get('order_id')
    )

    signature = (
        request.POST.get('razorpay_signature')
        or request.POST.get('signature')
        or request.GET.get('razorpay_signature')
        or request.GET.get('signature')
    )

    # Check payment information
    if not payment_id or not order_id or not signature:

        return render(
            request,
            'resume/payment_failed.html',
            {
                'error':
                    'Payment information is incomplete.'
            }
        )

    # Check that order belongs to this session
    session_order_id = request.session.get(
        'razorpay_order_id'
    )

    if session_order_id != order_id:

        return render(
            request,
            'resume/payment_failed.html',
            {
                'error':
                    'Invalid payment order.'
            }
        )

    try:

        # Razorpay client
        client = razorpay.Client(
            auth=(
                settings.RAZORPAY_KEY_ID,
                settings.RAZORPAY_KEY_SECRET
            )
        )

        # Payment verification data
        verification_data = {

            'razorpay_order_id':
                order_id,

            'razorpay_payment_id':
                payment_id,

            'razorpay_signature':
                signature
        }

        # Verify Razorpay signature
        client.utility.verify_payment_signature(
            verification_data
        )

        # Get resume
        resume_id = request.session.get(
            'resume_id'
        )

        if not resume_id:

            return render(
                request,
                'resume/payment_failed.html',
                {
                    'error':
                        'Resume information is missing.'
                }
            )

        resume = get_object_or_404(
            Resume,
            id=resume_id,
            user=request.user
        )

        # ======================================
        # MARK RESUME AS PAID
        # ======================================

        resume.payment_status = 'Paid'

        resume.payment_id = payment_id

        resume.payment_amount = 50.00

        # ======================================
        # MAKE THIS RESUME THE DEFAULT RESUME
        # ======================================

        Resume.objects.filter(
            user=request.user
        ).exclude(
            id=resume.id
        ).update(
            is_default=False
        )

        resume.is_default = True

        resume.save()

        # ======================================
        # CREATE INVOICE NUMBER
        # ======================================

        invoice_number = (
            f'INV-{timezone.now().strftime("%Y%m%d")}-'
            f'{uuid.uuid4().hex[:8].upper()}'
        )

        # ======================================
        # PAYMENT HISTORY
        # ======================================

        payment_record = (
            ResumePayment.objects.filter(
                payment_id=payment_id
            ).first()
        )

        if not payment_record:

            ResumePayment.objects.create(
                resume=resume,
                user=request.user,
                amount=50.00,
                payment_id=payment_id,
                invoice_number=invoice_number,
                status='Paid'
            )

        # ======================================
        # RESUME VERSION
        # ======================================

        latest_version = (
            ResumeVersion.objects.filter(
                resume=resume
            ).order_by(
                '-version_number'
            ).first()
        )

        if latest_version:

            next_version = (
                latest_version.version_number + 1
            )

        else:

            next_version = 1

        ResumeVersion.objects.create(
            resume=resume,
            version_number=next_version
        )

        # ======================================
        # PAYMENT VERIFIED
        # ======================================

        request.session[
            'payment_verified'
        ] = True

        request.session[
            'payment_id'
        ] = payment_id

        request.session[
            'invoice_number'
        ] = invoice_number

        return redirect(
            'resume_success'
        )

    except razorpay.errors.SignatureVerificationError:

        return render(
            request,
            'resume/payment_failed.html',
            {
                'error':
                    'Payment verification failed.'
            }
        )

    except Exception:

        return render(
            request,
            'resume/payment_failed.html',
            {
                'error':
                    'Unable to verify payment.'
            }
        )


# ==========================================
# RESUME SUCCESS PAGE
# ==========================================

@login_required
def resume_success(request):

    # Payment must be verified
    payment_verified = request.session.get(
        'payment_verified',
        False
    )

    if not payment_verified:

        return redirect(
            'resume_payment'
        )

    # Get resume from session
    resume_id = request.session.get(
        'resume_id'
    )

    if not resume_id:

        return redirect(
            'create_resume'
        )

    resume = get_object_or_404(
        Resume,
        id=resume_id,
        user=request.user
    )

    # Get latest payment
    payment = (
        ResumePayment.objects.filter(
            resume=resume,
            user=request.user,
            status='Paid'
        ).order_by(
            '-created_at'
        ).first()
    )

    # Get latest version
    version = (
        ResumeVersion.objects.filter(
            resume=resume
        ).order_by(
            '-version_number'
        ).first()
    )

    return render(
        request,
        'resume/success.html',
        {
            'resume': resume,
            'payment': payment,
            'version': version
        }
    )


# ==========================================
# DOWNLOAD RESUME PDF
# ==========================================

@login_required
def download_resume_pdf(
    request,
    resume_id
):

    # Get user's resume
    resume = get_object_or_404(
        Resume,
        id=resume_id,
        user=request.user
    )

    # Payment must be completed
    if resume.payment_status != 'Paid':

        return redirect(
            'resume_payment'
        )

    # ==========================================
    # CREATE PDF RESPONSE
    # ==========================================

    response = HttpResponse(
        content_type='application/pdf'
    )

    response[
        'Content-Disposition'
    ] = (
        'attachment; '
        f'filename="{resume.full_name}_Resume.pdf"'
    )

    # Create PDF
    pdf = canvas.Canvas(
        response,
        pagesize=A4
    )

    width, height = A4

    x = 25 * mm
    y = height - 25 * mm

    # ==========================================
    # NAME
    # ==========================================

    pdf.setFont(
        "Helvetica-Bold",
        20
    )

    pdf.drawString(
        x,
        y,
        resume.full_name[:80]
    )

    y -= 10 * mm

    # ==========================================
    # CONTACT
    # ==========================================

    pdf.setFont(
        "Helvetica",
        10
    )

    contact = resume.email

    if resume.phone:

        contact += (
            " | "
            + resume.phone
        )

    pdf.drawString(
        x,
        y,
        contact[:120]
    )

    y -= 15 * mm

    # ==========================================
    # SECTION FUNCTION
    # ==========================================

    def add_section(
        title,
        text
    ):

        nonlocal y

        if not text:

            return

        # New page if needed
        if y < 35 * mm:

            pdf.showPage()

            y = height - 25 * mm

        # Section title
        pdf.setFont(
            "Helvetica-Bold",
            12
        )

        pdf.drawString(
            x,
            y,
            title
        )

        y -= 7 * mm

        # Section text
        pdf.setFont(
            "Helvetica",
            10
        )

        lines = text.splitlines()

        for line in lines:

            if y < 20 * mm:

                pdf.showPage()

                y = height - 25 * mm

            pdf.drawString(
                x,
                y,
                line[:100]
            )

            y -= 5 * mm

        y -= 5 * mm

    # ==========================================
    # ADD RESUME SECTIONS
    # ==========================================

    add_section(
        "Career Objective",
        resume.career_objective
    )

    add_section(
        "Education",
        resume.education
    )

    add_section(
        "Skills",
        resume.skills
    )

    add_section(
        "Work Experience",
        resume.work_experience
    )

    add_section(
        "Internships",
        resume.internships
    )

    add_section(
        "Projects",
        resume.projects
    )

    add_section(
        "Certifications",
        resume.certifications
    )

    add_section(
        "Achievements",
        resume.achievements
    )

    add_section(
        "Languages",
        resume.languages
    )

    add_section(
        "Social Links",
        resume.social_links
    )

    add_section(
        "References",
        resume.references
    )

    # ==========================================
    # FINISH PDF
    # ==========================================

    pdf.save()

    # ==========================================
    # DOWNLOAD HISTORY
    # ==========================================

    ResumeDownloadHistory.objects.create(
        resume=resume,
        user=request.user
    )

    # Update download count
    resume.download_count += 1

    resume.last_downloaded_at = timezone.now()

    resume.save(
        update_fields=[
            'download_count',
            'last_downloaded_at',
            'updated_at'
        ]
    )

    return response


# ==========================================
# SET DEFAULT RESUME
# ==========================================

@login_required
def set_default_resume(
    request,
    resume_id
):

    resume = get_object_or_404(
        Resume,
        id=resume_id,
        user=request.user
    )

    # Remove default from other resumes
    Resume.objects.filter(
        user=request.user
    ).update(
        is_default=False
    )

    # Make selected resume default
    resume.is_default = True

    resume.save(
        update_fields=[
            'is_default',
            'updated_at'
        ]
    )

    return redirect(
        'resume_success'
    )