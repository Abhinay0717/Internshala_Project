from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.sessions.models import Session
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.timezone import localtime
from django.contrib.auth import update_session_auth_hash

from .forms import ForgotPasswordForm, RegisterForm

from .models import (
    PasswordResetRequest,
    UserProfile,
    LanguageChangeOTP,
    LoginHistory,
    LoginOTP,
    TrustedDevice,
    ActiveSession,
    LoginVerificationLog
)

from resume.models import Resume, ResumeOTP
from resume.forms import ResumeForm, OTPForm

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

import razorpay
import random
import re
import uuid

from datetime import timedelta
from zoneinfo import ZoneInfo


# ==========================================================
# HOME
# ==========================================================

def home(request):
    return render(
        request,
        'home.html'
    )
# ==========================================================
# REGISTER
# ==========================================================

def register(request):

    if request.method == 'POST':

        form = RegisterForm(request.POST)

        if form.is_valid():

            username = form.cleaned_data['username'].strip()
            email = form.cleaned_data['email'].strip().lower()
            password = form.cleaned_data['password']

            # Check username
            if User.objects.filter(username=username).exists():

                return render(
                    request,
                    'register.html',
                    {
                        'form': form,
                        'error': 'Username already exists.'
                    }
                )

            # Check email
            if User.objects.filter(email__iexact=email).exists():

                return render(
                    request,
                    'register.html',
                    {
                        'form': form,
                        'error': 'Email is already registered.'
                    }
                )

            # Create user securely
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )

            # Create user profile
            UserProfile.objects.get_or_create(
                user=user
            )

            return redirect('login')

    else:

        form = RegisterForm()

    return render(
        request,
        'register.html',
        {
            'form': form
        }
    )

# ==========================================================
# LOGIN SECURITY HELPERS
# ==========================================================

def get_client_ip(request):
    forwarded = request.META.get(
        'HTTP_X_FORWARDED_FOR'
    )

    if forwarded:
        return forwarded.split(',')[0].strip()

    return request.META.get(
        'REMOTE_ADDR'
    )


def get_browser_info(user_agent):
    user_agent = user_agent or ''

    # Google Chrome
    if (
        'Chrome/' in user_agent
        and 'Edg/' not in user_agent
        and 'OPR/' not in user_agent
        and 'Brave' not in user_agent
    ):
        browser_name = 'Google Chrome'

        match = re.search(
            r'Chrome/([\d.]+)',
            user_agent
        )

        browser_version = (
            match.group(1)
            if match
            else ''
        )

    # Microsoft Edge
    elif 'Edg/' in user_agent:
        browser_name = 'Microsoft Edge'

        match = re.search(
            r'Edg/([\d.]+)',
            user_agent
        )

        browser_version = (
            match.group(1)
            if match
            else ''
        )

    # Firefox
    elif 'Firefox/' in user_agent:
        browser_name = 'Mozilla Firefox'

        match = re.search(
            r'Firefox/([\d.]+)',
            user_agent
        )

        browser_version = (
            match.group(1)
            if match
            else ''
        )

    # Safari
    elif (
        'Safari/' in user_agent
        and 'Chrome/' not in user_agent
    ):
        browser_name = 'Safari'

        match = re.search(
            r'Version/([\d.]+)',
            user_agent
        )

        browser_version = (
            match.group(1)
            if match
            else ''
        )

    else:
        browser_name = 'Unknown'
        browser_version = ''

    return browser_name, browser_version


def get_device_info(user_agent):
    user_agent = user_agent or ''

    # Mobile
    if (
        'iPhone' in user_agent
        or (
            'Android' in user_agent
            and 'Mobile' in user_agent
        )
    ):
        device_type = 'mobile'

    # Tablet
    elif (
        'iPad' in user_agent
        or (
            'Android' in user_agent
            and 'Mobile' not in user_agent
        )
    ):
        device_type = 'tablet'

    # Desktop / Laptop
    elif (
        'Windows' in user_agent
        or 'Macintosh' in user_agent
        or 'Linux' in user_agent
    ):
        device_type = 'desktop'

    else:
        device_type = 'unknown'

    device_model = ''

    # Android device model
    android_match = re.search(
        r'Android [^;]+;\s*([^;)]+?)(?:\s+Build/|\))',
        user_agent
    )

    if android_match:
        device_model = (
            android_match.group(1).strip()
        )

    elif 'iPhone' in user_agent:
        device_model = 'iPhone'

    elif 'iPad' in user_agent:
        device_model = 'iPad'

    return device_type, device_model


def get_operating_system(user_agent):
    user_agent = user_agent or ''

    if 'Windows NT 10.0' in user_agent:
        return 'Windows 10/11'

    if 'Windows NT 6.3' in user_agent:
        return 'Windows 8.1'

    if 'Android' in user_agent:
        match = re.search(
            r'Android ([\d.]+)',
            user_agent
        )

        if match:
            return (
                f'Android {match.group(1)}'
            )

        return 'Android'

    if 'iPhone OS' in user_agent:
        match = re.search(
            r'iPhone OS ([\d_]+)',
            user_agent
        )

        if match:
            return (
                'iOS '
                + match.group(1).replace(
                    '_',
                    '.'
                )
            )

        return 'iOS'

    if 'iPad' in user_agent:
        match = re.search(
            r'CPU OS ([\d_]+)',
            user_agent
        )

        if match:
            return (
                'iPadOS '
                + match.group(1).replace(
                    '_',
                    '.'
                )
            )

        return 'iPadOS'

    if 'Mac OS X' in user_agent:
        return 'macOS'

    if 'Linux' in user_agent:
        return 'Linux'

    return 'Unknown'


def get_approximate_location(ip_address):
    if ip_address in [
        '127.0.0.1',
        '::1',
        'localhost'
    ]:
        return 'Local development'

    return 'Unknown'


def get_device_identifier(request):
    device_id = request.COOKIES.get(
        'login_device_id'
    )

    if not device_id:
        device_id = str(
            uuid.uuid4()
        )

    return device_id


def is_google_chrome(browser_name):
    return browser_name == 'Google Chrome'


# ==========================================================
# LOGIN
# ==========================================================

def user_login(request):

    if request.method != 'POST':
        return render(
            request,
            'login.html'
        )

    username = request.POST.get(
        'username',
        ''
    ).strip()

    password = request.POST.get(
        'password',
        ''
    )

    user_agent = request.META.get(
        'HTTP_USER_AGENT',
        ''
    )

    ip_address = get_client_ip(
        request
    )

    browser_name, browser_version = (
        get_browser_info(
            user_agent
        )
    )

    device_type, device_model = (
        get_device_info(
            user_agent
        )
    )

    operating_system = (
        get_operating_system(
            user_agent
        )
    )

    approximate_location = (
        get_approximate_location(
            ip_address
        )
    )

    # ------------------------------------------------------
    # AUTHENTICATE USERNAME + PASSWORD
    # ------------------------------------------------------

    user = authenticate(
        request,
        username=username,
        password=password
    )

    if user is None:

        attempted_user = User.objects.filter(
            username=username
        ).first()

        LoginHistory.objects.create(
            user=attempted_user,
            browser_name=browser_name,
            browser_version=browser_version,
            operating_system=operating_system,
            device_type=device_type,
            device_model=device_model,
            ip_address=ip_address,
            approximate_location=approximate_location,
            status='failed',
            failure_reason='Invalid username or password.',
        )

        return render(
            request,
            'login.html',
            {
                'error':
                    'Invalid username or password.'
            }
        )

    # ------------------------------------------------------
    # MOBILE LOGIN TIME RESTRICTION
    # 10:00 AM - 1:00 PM IST
    # ------------------------------------------------------

    if device_type == 'mobile':

        india_time = localtime(
            timezone.now(),
            ZoneInfo('Asia/Kolkata')
        )

        current_time = india_time.time()

        start_time = current_time.replace(
            hour=10,
            minute=0,
            second=0,
            microsecond=0
        )

        end_time = current_time.replace(
            hour=13,
            minute=0,
            second=0,
            microsecond=0
        )

        if not (
            start_time <= current_time <= end_time
        ):

            LoginHistory.objects.create(
                user=user,
                browser_name=browser_name,
                browser_version=browser_version,
                operating_system=operating_system,
                device_type=device_type,
                device_model=device_model,
                ip_address=ip_address,
                approximate_location=approximate_location,
                status='blocked',
                failure_reason=(
                    'Mobile login is allowed only '
                    'between 10:00 AM and 1:00 PM IST.'
                ),
                is_new_browser=True,
                is_new_device=True,
                is_new_ip=True,
                otp_required=False
            )

            LoginVerificationLog.objects.create(
                user=user,
                verification_type='blocked',
                ip_address=ip_address,
                browser=browser_name,
                device=(
                    device_model
                    or device_type
                ),
                message=(
                    'Mobile login blocked outside '
                    'the permitted time.'
                )
            )

            return render(
                request,
                'login.html',
                {
                    'error': (
                        'Mobile login is allowed only '
                        'between 10:00 AM and 1:00 PM IST.'
                    )
                }
            )

    # ------------------------------------------------------
    # DEVICE IDENTIFIER
    # ------------------------------------------------------

    device_identifier = get_device_identifier(
        request
    )

    # ------------------------------------------------------
    # NEW BROWSER / DEVICE / IP
    # ------------------------------------------------------

    is_new_browser = not LoginHistory.objects.filter(
        user=user,
        browser_name=browser_name,
        browser_version=browser_version
    ).exists()

    is_new_device = not TrustedDevice.objects.filter(
        user=user,
        device_identifier=device_identifier,
        is_active=True
    ).exists()

    is_new_ip = not LoginHistory.objects.filter(
        user=user,
        ip_address=ip_address
    ).exists()

    # ------------------------------------------------------
    # OTP REQUIREMENT
    # ------------------------------------------------------

    chrome_login = is_google_chrome(
        browser_name
    )

    otp_required = (
        chrome_login
        or is_new_browser
        or is_new_device
        or is_new_ip
    )

    # ------------------------------------------------------
    # LOGIN HISTORY
    # ------------------------------------------------------

    login_history = LoginHistory.objects.create(
        user=user,
        browser_name=browser_name,
        browser_version=browser_version,
        operating_system=operating_system,
        device_type=device_type,
        device_model=device_model,
        ip_address=ip_address,
        approximate_location=approximate_location,
        status=(
            'otp_required'
            if otp_required
            else 'success'
        ),
        is_new_browser=is_new_browser,
        is_new_device=is_new_device,
        is_new_ip=is_new_ip,
        otp_required=otp_required,
        otp_verified=False,
        is_trusted_device=False
    )

    # ------------------------------------------------------
    # OTP REQUIRED
    # ------------------------------------------------------

    if otp_required:

        LoginOTP.objects.filter(
            user=user,
            is_verified=False,
            is_expired=False
        ).update(
            is_expired=True
        )

        otp = generate_otp()

        login_otp = LoginOTP.objects.create(
            user=user,
            otp=otp,
            expires_at=(
                timezone.now()
                + timedelta(minutes=5)
            ),
            login_history=login_history
        )

        request.session[
            'pending_login_user_id'
        ] = user.id

        request.session[
            'pending_login_history_id'
        ] = login_history.id

        request.session[
            'pending_login_otp_id'
        ] = login_otp.id

        request.session[
            'pending_device_identifier'
        ] = device_identifier

        request.session[
            'pending_login_browser'
        ] = browser_name

        request.session[
            'pending_login_device'
        ] = device_type

        LoginVerificationLog.objects.create(
            user=user,
            login_history=login_history,
            verification_type='otp_sent',
            ip_address=ip_address,
            browser=browser_name,
            device=(
                device_model
                or device_type
            ),
            message=(
                'Login OTP sent for '
                f'{browser_name} login.'
            )
        )

        send_mail(
            subject='Login Verification OTP',
            message=(
                f'Your login verification OTP is: '
                f'{otp}\n\n'
                'This OTP is valid for 5 minutes.'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[
                user.email
            ],
            fail_silently=False
        )

        response = redirect(
            'verify_login_otp'
        )

        response.set_cookie(
            'login_device_id',
            device_identifier,
            max_age=60 * 60 * 24 * 365,
            httponly=True,
            samesite='Lax'
        )

        return response

    # ------------------------------------------------------
    # DIRECT LOGIN
    # ------------------------------------------------------

    login(
        request,
        user
    )

    login_history.status = 'success'
    login_history.otp_verified = True
    login_history.is_trusted_device = True
    login_history.session_key = (
        request.session.session_key
        or ''
    )

    login_history.save(
        update_fields=[
            'status',
            'otp_verified',
            'is_trusted_device',
            'session_key'
        ]
    )

    # ------------------------------------------------------
    # TRUST DEVICE
    # ------------------------------------------------------

    TrustedDevice.objects.update_or_create(
        user=user,
        device_identifier=device_identifier,
        defaults={
            'browser_name': browser_name,
            'browser_version': browser_version,
            'operating_system': operating_system,
            'device_type': device_type,
            'device_model': device_model,
            'last_ip_address': ip_address,
            'is_active': True
        }
    )

    # ------------------------------------------------------
    # ACTIVE SESSION
    # ------------------------------------------------------

    ActiveSession.objects.update_or_create(
        session_key=request.session.session_key,
        defaults={
            'user': user,
            'browser_name': browser_name,
            'browser_version': browser_version,
            'operating_system': operating_system,
            'device_type': device_type,
            'device_model': device_model,
            'ip_address': ip_address,
            'is_active': True
        }
    )

    LoginVerificationLog.objects.create(
        user=user,
        login_history=login_history,
        verification_type='success',
        ip_address=ip_address,
        browser=browser_name,
        device=(
            device_model
            or device_type
        ),
        message='Login completed successfully.'
    )

    # ------------------------------------------------------
    # FORCE PASSWORD CHANGE
    # ------------------------------------------------------

    try:

        profile = UserProfile.objects.get(
            user=user
        )

        if profile.must_change_password:

            response = redirect(
                'change_password'
            )

            response.set_cookie(
                'login_device_id',
                device_identifier,
                max_age=60 * 60 * 24 * 365,
                httponly=True,
                samesite='Lax'
            )

            return response

    except UserProfile.DoesNotExist:
        pass

    response = redirect(
        'public_space'
    )

    response.set_cookie(
        'login_device_id',
        device_identifier,
        max_age=60 * 60 * 24 * 365,
        httponly=True,
        samesite='Lax'
    )

    return response


# ==========================================================
# VERIFY LOGIN OTP
# ==========================================================

def verify_login_otp(request):

    otp_id = request.session.get(
        'pending_login_otp_id'
    )

    history_id = request.session.get(
        'pending_login_history_id'
    )

    user_id = request.session.get(
        'pending_login_user_id'
    )

    if not otp_id or not history_id or not user_id:
        return redirect(
            'login'
        )

    try:

        login_otp = LoginOTP.objects.get(
            id=otp_id
        )

        login_history = LoginHistory.objects.get(
            id=history_id
        )

        user = User.objects.get(
            id=user_id
        )

    except (
        LoginOTP.DoesNotExist,
        LoginHistory.DoesNotExist,
        User.DoesNotExist
    ):

        request.session.pop(
            'pending_login_otp_id',
            None
        )

        request.session.pop(
            'pending_login_history_id',
            None
        )

        request.session.pop(
            'pending_login_user_id',
            None
        )

        return redirect(
            'login'
        )

    # ------------------------------------------------------
    # ALREADY VERIFIED
    # ------------------------------------------------------

    if login_otp.is_verified:
        return redirect(
            'login'
        )

    # ------------------------------------------------------
    # CHECK EXPIRY
    # ------------------------------------------------------

    if timezone.now() > login_otp.expires_at:

        login_otp.is_expired = True

        login_otp.save(
            update_fields=[
                'is_expired'
            ]
        )

        login_history.status = 'otp_failed'

        login_history.failure_reason = (
            'Login OTP expired.'
        )

        login_history.save(
            update_fields=[
                'status',
                'failure_reason'
            ]
        )

        LoginVerificationLog.objects.create(
            user=user,
            login_history=login_history,
            verification_type='otp_expired',
            ip_address=get_client_ip(request),
            browser=login_history.browser_name,
            device=(
                login_history.device_model
                or login_history.device_type
            ),
            message='Login OTP expired.'
        )

        return render(
            request,
            'verify_login_otp.html',
            {
                'error': (
                    'OTP has expired. '
                    'Please return to login '
                    'and request a new OTP.'
                )
            }
        )

    # ------------------------------------------------------
    # VERIFY OTP
    # ------------------------------------------------------

    if request.method == 'POST':

        entered_otp = request.POST.get(
            'otp',
            ''
        ).strip()

        # --------------------------------------------------
        # MAXIMUM ATTEMPTS
        # --------------------------------------------------

        if login_otp.verification_attempts >= 5:

            login_history.status = 'blocked'

            login_history.failure_reason = (
                'Maximum OTP verification attempts reached.'
            )

            login_history.save(
                update_fields=[
                    'status',
                    'failure_reason'
                ]
            )

            LoginVerificationLog.objects.create(
                user=user,
                login_history=login_history,
                verification_type='blocked',
                ip_address=get_client_ip(request),
                browser=login_history.browser_name,
                device=(
                    login_history.device_model
                    or login_history.device_type
                ),
                message=(
                    'Maximum login OTP attempts reached.'
                )
            )

            return render(
                request,
                'verify_login_otp.html',
                {
                    'error': (
                        'Too many invalid OTP attempts. '
                        'Please return to the login page '
                        'and try again.'
                    )
                }
            )

        # --------------------------------------------------
        # CORRECT OTP
        # --------------------------------------------------

        if entered_otp == login_otp.otp:

            login_otp.is_verified = True

            login_otp.save(
                update_fields=[
                    'is_verified'
                ]
            )

            login(
                request,
                user
            )

            session_key = (
                request.session.session_key
                or ''
            )

            # Update login history
            login_history.status = 'success'
            login_history.otp_verified = True
            login_history.is_trusted_device = True
            login_history.session_key = session_key

            login_history.save(
                update_fields=[
                    'status',
                    'otp_verified',
                    'is_trusted_device',
                    'session_key'
                ]
            )

            # ------------------------------------------------
            # TRUST DEVICE
            # ------------------------------------------------

            device_identifier = request.session.get(
                'pending_device_identifier'
            )

            if not device_identifier:
                device_identifier = (
                    get_device_identifier(
                        request
                    )
                )

            TrustedDevice.objects.update_or_create(
                user=user,
                device_identifier=device_identifier,
                defaults={
                    'browser_name':
                        login_history.browser_name,

                    'browser_version':
                        login_history.browser_version,

                    'operating_system':
                        login_history.operating_system,

                    'device_type':
                        login_history.device_type,

                    'device_model':
                        login_history.device_model,

                    'last_ip_address':
                        get_client_ip(request),

                    'is_active':
                        True
                }
            )

            # ------------------------------------------------
            # ACTIVE SESSION
            # ------------------------------------------------

            ActiveSession.objects.update_or_create(
                session_key=session_key,
                defaults={
                    'user': user,

                    'browser_name':
                        login_history.browser_name,

                    'browser_version':
                        login_history.browser_version,

                    'operating_system':
                        login_history.operating_system,

                    'device_type':
                        login_history.device_type,

                    'device_model':
                        login_history.device_model,

                    'ip_address':
                        get_client_ip(request),

                    'is_active':
                        True
                }
            )

            # ------------------------------------------------
            # VERIFICATION LOG
            # ------------------------------------------------

            LoginVerificationLog.objects.create(
                user=user,
                login_history=login_history,
                verification_type='otp_verified',
                ip_address=get_client_ip(request),
                browser=login_history.browser_name,
                device=(
                    login_history.device_model
                    or login_history.device_type
                ),
                message=(
                    'Login OTP verified successfully.'
                )
            )

            LoginVerificationLog.objects.create(
                user=user,
                login_history=login_history,
                verification_type='success',
                ip_address=get_client_ip(request),
                browser=login_history.browser_name,
                device=(
                    login_history.device_model
                    or login_history.device_type
                ),
                message=(
                    'Login completed successfully.'
                )
            )

            # ------------------------------------------------
            # CLEAR PENDING LOGIN DATA
            # ------------------------------------------------

            request.session.pop(
                'pending_login_otp_id',
                None
            )

            request.session.pop(
                'pending_login_history_id',
                None
            )

            request.session.pop(
                'pending_login_user_id',
                None
            )

            request.session.pop(
                'pending_login_browser',
                None
            )

            request.session.pop(
                'pending_login_device',
                None
            )

            request.session.pop(
                'pending_device_identifier',
                None
            )

            # ------------------------------------------------
            # PASSWORD CHANGE CHECK
            # ------------------------------------------------

            try:

                profile = UserProfile.objects.get(
                    user=user
                )

                if profile.must_change_password:
                    response = redirect(
                        'change_password'
                    )
                else:
                    response = redirect(
                        'public_space'
                    )

            except UserProfile.DoesNotExist:

                response = redirect(
                    'public_space'
                )

            response.set_cookie(
                'login_device_id',
                device_identifier,
                max_age=60 * 60 * 24 * 365,
                httponly=True,
                samesite='Lax'
            )

            return response

        # --------------------------------------------------
        # INVALID OTP
        # --------------------------------------------------

        login_otp.verification_attempts += 1

        login_otp.save(
            update_fields=[
                'verification_attempts'
            ]
        )

        ip_address = get_client_ip(
            request
        )

        approximate_location = (
            get_approximate_location(
                ip_address
            )
        )

        login_history.status = 'otp_failed'

        login_history.ip_address = ip_address

        login_history.approximate_location = (
            approximate_location
        )

        login_history.otp_required = True

        login_history.otp_verified = False

        login_history.failure_reason = (
            'Invalid login OTP.'
        )

        login_history.save(
            update_fields=[
                'status',
                'ip_address',
                'approximate_location',
                'otp_required',
                'otp_verified',
                'failure_reason'
            ]
        )

        LoginVerificationLog.objects.create(
            user=user,
            login_history=login_history,
            verification_type='otp_failed',
            ip_address=ip_address,
            browser=login_history.browser_name,
            device=(
                login_history.device_model
                or login_history.device_type
            ),
            message='Invalid login OTP.'
        )

        remaining_attempts = (
            5 - login_otp.verification_attempts
        )

        # --------------------------------------------------
        # MAXIMUM ATTEMPTS REACHED
        # --------------------------------------------------

        if remaining_attempts <= 0:

            login_history.status = 'blocked'

            login_history.failure_reason = (
                'Maximum OTP attempts reached.'
            )

            login_history.save(
                update_fields=[
                    'status',
                    'failure_reason'
                ]
            )

            LoginVerificationLog.objects.create(
                user=user,
                login_history=login_history,
                verification_type='blocked',
                ip_address=ip_address,
                browser=login_history.browser_name,
                device=(
                    login_history.device_model
                    or login_history.device_type
                ),
                message=(
                    'Maximum OTP attempts reached.'
                )
            )

            return render(
                request,
                'verify_login_otp.html',
                {
                    'error': (
                        'Maximum OTP attempts reached. '
                        'Login blocked.'
                    )
                }
            )

        # --------------------------------------------------
        # OTP STILL ALLOWED
        # --------------------------------------------------

        return render(
            request,
            'verify_login_otp.html',
            {
                'error': 'Invalid OTP.',
                'remaining_attempts': remaining_attempts
            }
        )

    # ------------------------------------------------------
    # GET REQUEST
    # ------------------------------------------------------

    return render(
        request,
        'verify_login_otp.html'
    )


# ==========================================================
# CHANGE PASSWORD
# ==========================================================

@login_required
def change_password(request):

    if request.method == 'POST':

        new_password = request.POST.get(
            'new_password',
            ''
        )

        confirm_password = request.POST.get(
            'confirm_password',
            ''
        )

        if not new_password or not confirm_password:

            return render(
                request,
                'change_password.html',
                {
                    'error':
                        'Please enter both password fields.'
                }
            )

        if new_password != confirm_password:

            return render(
                request,
                'change_password.html',
                {
                    'error':
                        'Passwords do not match.'
                }
            )

        if len(new_password) < 8:

            return render(
                request,
                'change_password.html',
                {
                    'error':
                        'Password must contain at least 8 characters.'
                }
            )

        request.user.set_password(
            new_password
        )

        request.user.save()

        try:

            profile = UserProfile.objects.get(
                user=request.user
            )

            profile.must_change_password = False

            profile.save(
                update_fields=[
                    'must_change_password'
                ]
            )

        except UserProfile.DoesNotExist:
            pass

        update_session_auth_hash(
            request,
            request.user
        )

        return redirect(
            'public_space'
        )

    return render(
        request,
        'change_password.html'
    )


# ==========================================================
# GENERATE OTP
# ==========================================================

def generate_otp():
    return str(
        random.randint(
            100000,
            999999
        )
    )


# ==========================================================
# SEND LANGUAGE OTP
# ==========================================================

@login_required
def send_language_otp(request):

    otp = generate_otp()

    LanguageChangeOTP.objects.create(
        user=request.user,
        otp=otp
    )

    send_mail(
        subject='French Language Change OTP',
        message=(
            f'Your OTP for changing the language '
            f'is {otp}.'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[
            request.user.email
        ],
        fail_silently=False
    )

    request.session[
        'language_otp_sent'
    ] = True

    return redirect(
        'verify_otp'
    )


# ==========================================================
# VERIFY LANGUAGE OTP
# ==========================================================

@login_required
def verify_otp(request):

    if request.method == 'POST':

        entered_otp = request.POST.get(
            'otp',
            ''
        ).strip()

        otp_record = LanguageChangeOTP.objects.filter(
            user=request.user,
            is_verified=False
        ).order_by(
            '-created_at'
        ).first()

        if not otp_record:

            return render(
                request,
                'verify_otp.html',
                {
                    'error':
                        'No active OTP found.'
                }
            )

        if entered_otp != otp_record.otp:

            return render(
                request,
                'verify_otp.html',
                {
                    'error':
                        'Invalid OTP.'
                }
            )

        otp_record.is_verified = True

        otp_record.save(
            update_fields=[
                'is_verified'
            ]
        )

        try:

            profile = UserProfile.objects.get(
                user=request.user
            )

            profile.language = 'fr'

            profile.save(
                update_fields=[
                    'language'
                ]
            )

        except UserProfile.DoesNotExist:

            UserProfile.objects.create(
                user=request.user,
                language='fr'
            )

        request.session[
            'language'
        ] = 'fr'

        request.session.pop(
            'language_otp_sent',
            None
        )

        return redirect(
            'home'
        )

    return render(
        request,
        'verify_otp.html'
    )


# ==========================================================
# FORGOT PASSWORD
# ==========================================================

def forgot_password(request):

    if request.method == 'POST':

        form = ForgotPasswordForm(
            request.POST
        )

        if form.is_valid():

            identifier = form.cleaned_data[
                'identifier'
            ].strip()

            reset_method = form.cleaned_data[
                'reset_method'
            ]

            user = None

            if reset_method == 'email':

                user = User.objects.filter(
                    email__iexact=identifier
                ).first()

            elif reset_method == 'mobile':

                try:

                    profile = UserProfile.objects.filter(
                        mobile=identifier
                    ).select_related(
                        'user'
                    ).first()

                    if profile:
                        user = profile.user

                except Exception:
                    user = None

            if not user:

                return render(
                    request,
                    'forgot_password.html',
                    {
                        'form': form,
                        'error':
                            'No account found with the provided details.'
                    }
                )

            # ------------------------------------------------
            # ONE RESET REQUEST PER 24 HOURS
            # ------------------------------------------------

            last_request = PasswordResetRequest.objects.filter(
                user=user,
                request_time__gte=(
                    timezone.now()
                    - timedelta(hours=24)
                )
            ).order_by(
                '-request_time'
            ).first()

            if last_request:

                return render(
                    request,
                    'forgot_password.html',
                    {
                        'form': form,
                        'error':
                            'You can use this option only once per day.'
                    }
                )

            otp = generate_otp()

            ip_address = get_client_ip(
                request
            )

            user_agent = request.META.get(
                'HTTP_USER_AGENT',
                ''
            )

            browser_name, browser_version = (
                get_browser_info(
                    user_agent
                )
            )

            device_type, device_model = (
                get_device_info(
                    user_agent
                )
            )

            browser_details = (
                f'{browser_name} '
                f'{browser_version}'
            )

            device_details = (
                f'{device_type} '
                f'{device_model}'
            )

            reset_request = (
                PasswordResetRequest.objects.create(
                    user=user,
                    reset_method=reset_method,
                    otp=otp,
                    ip_address=ip_address,
                    browser=browser_details,
                    device=device_details
                )
            )

            request.session[
                'password_reset_request_id'
            ] = reset_request.id

            if reset_method == 'email':

                send_mail(
                    subject='Password Reset OTP',
                    message=(
                        f'Your password reset OTP is: '
                        f'{otp}\n\n'
                        'This OTP is valid for 5 minutes.'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[
                        user.email
                    ],
                    fail_silently=False
                )

            else:

                print(
                    f'Password Reset OTP for '
                    f'{user.username}: {otp}'
                )

            return redirect(
                'verify_password_reset_otp'
            )

    else:

        form = ForgotPasswordForm()

    return render(
        request,
        'forgot_password.html',
        {
            'form': form
        }
    )


# ==========================================================
# VERIFY PASSWORD RESET OTP
# ==========================================================

def verify_password_reset_otp(request):

    reset_request_id = request.session.get(
        'password_reset_request_id'
    )

    if not reset_request_id:

        return redirect(
            'forgot_password'
        )

    try:

        reset_request = PasswordResetRequest.objects.get(
            id=reset_request_id
        )

    except PasswordResetRequest.DoesNotExist:

        return redirect(
            'forgot_password'
        )

    # ------------------------------------------------------
    # OTP EXPIRY
    # ------------------------------------------------------

    if timezone.now() > (
        reset_request.otp_created_at
        + timedelta(minutes=5)
    ):

        return render(
            request,
            'verify_password_reset_otp.html',
            {
                'error':
                    'OTP has expired. Please try again.'
            }
        )

    if request.method == 'POST':

        entered_otp = request.POST.get(
            'otp',
            ''
        ).strip()

        # --------------------------------------------------
        # MAXIMUM ATTEMPTS
        # --------------------------------------------------

        if reset_request.verification_attempts >= 5:

            return render(
                request,
                'verify_password_reset_otp.html',
                {
                    'error':
                        'Maximum OTP attempts reached.'
                }
            )

        # --------------------------------------------------
        # CORRECT OTP
        # --------------------------------------------------

        if entered_otp == reset_request.otp:

            reset_request.otp_verified = True

            reset_request.save(
                update_fields=[
                    'otp_verified'
                ]
            )

            request.session[
                'password_reset_verified'
            ] = True

            return redirect(
                'complete_password_reset'
            )

        # --------------------------------------------------
        # INVALID OTP
        # --------------------------------------------------

        reset_request.verification_attempts += 1

        reset_request.save(
            update_fields=[
                'verification_attempts'
            ]
        )

        remaining = (
            5
            - reset_request.verification_attempts
        )

        return render(
            request,
            'verify_password_reset_otp.html',
            {
                'error':
                    'Invalid OTP.',
                'remaining_attempts':
                    remaining
            }
        )

    return render(
        request,
        'verify_password_reset_otp.html'
    )


# ==========================================================
# COMPLETE PASSWORD RESET
# ==========================================================

def complete_password_reset(request):

    reset_request_id = request.session.get(
        'password_reset_request_id'
    )

    verified = request.session.get(
        'password_reset_verified'
    )

    if not reset_request_id or not verified:

        return redirect(
            'forgot_password'
        )

    try:

        reset_request = PasswordResetRequest.objects.get(
            id=reset_request_id
        )

    except PasswordResetRequest.DoesNotExist:

        return redirect(
            'forgot_password'
        )

    if reset_request.reset_completed:

        return redirect(
            'login'
        )

    if request.method == 'POST':

        new_password = request.POST.get(
            'new_password',
            ''
        )

        confirm_password = request.POST.get(
            'confirm_password',
            ''
        )

        if not new_password or not confirm_password:

            return render(
                request,
                'password_reset_success.html',
                {
                    'error':
                        'Please enter both password fields.'
                }
            )

        if new_password != confirm_password:

            return render(
                request,
                'password_reset_success.html',
                {
                    'error':
                        'Passwords do not match.'
                }
            )

        if len(new_password) < 8:

            return render(
                request,
                'password_reset_success.html',
                {
                    'error':
                        'Password must contain at least 8 characters.'
                }
            )

        user = reset_request.user

        user.set_password(
            new_password
        )

        user.save()

        try:

            profile = UserProfile.objects.get(
                user=user
            )

            profile.must_change_password = False

            profile.save(
                update_fields=[
                    'must_change_password'
                ]
            )

        except UserProfile.DoesNotExist:
            pass

        reset_request.reset_completed = True

        reset_request.save(
            update_fields=[
                'reset_completed'
            ]
        )

        request.session.pop(
            'password_reset_request_id',
            None
        )

        request.session.pop(
            'password_reset_verified',
            None
        )

        return redirect(
            'login'
        )

    return render(
        request,
        'password_reset_success.html'
    )


# ==========================================================
# LOGIN HISTORY
# ==========================================================

@login_required
def login_history(request):

    history = LoginHistory.objects.filter(
        user=request.user
    ).order_by(
        '-login_time'
    )

    return render(
        request,
        'login_history.html',
        {
            'history': history
        }
    )


# ==========================================================
# ACTIVE SESSIONS
# ==========================================================

@login_required
def active_sessions(request):

    current_session_key = (
        request.session.session_key
    )

    sessions = ActiveSession.objects.filter(
        user=request.user,
        is_active=True
    ).order_by(
        '-last_activity'
    )

    return render(
        request,
        'active_sessions.html',
        {
            'sessions': sessions,
            'current_session_key':
                current_session_key
        }
    )


# ==========================================================
# LOG OUT OTHER DEVICES
# ==========================================================

@login_required
def logout_other_devices(request):

    if request.method == 'POST':

        current_session_key = (
            request.session.session_key
        )

        other_sessions = ActiveSession.objects.filter(
            user=request.user,
            is_active=True
        ).exclude(
            session_key=current_session_key
        )

        for active_session in other_sessions:

            Session.objects.filter(
                session_key=active_session.session_key
            ).delete()

            active_session.is_active = False

            active_session.save(
                update_fields=[
                    'is_active'
                ]
            )

        return redirect(
            'active_sessions'
        )

    return redirect(
        'active_sessions'
    )


# ==========================================================
# PROFILE
# ==========================================================

@login_required
def profile(request):

    # ------------------------------------------------------
    # LOGIN HISTORY
    # ------------------------------------------------------

    history = LoginHistory.objects.filter(
        user=request.user
    ).order_by(
        '-login_time'
    )

    # ------------------------------------------------------
    # SUBSCRIPTION INFORMATION
    # ------------------------------------------------------

    from subscriptions.models import UserSubscription

    subscription = UserSubscription.objects.filter(
        user=request.user,
        status='active'
    ).select_related(
        'plan'
    ).order_by(
        '-created_at'
    ).first()

    # Check subscription expiry and quota reset
    if subscription:

        subscription.check_and_reset_quota()

        subscription.refresh_from_db()

    # ------------------------------------------------------
    # PROFILE PAGE
    # ------------------------------------------------------

    return render(
        request,
        'profile.html',
        {
            'user': request.user,
            'history': history,
            'subscription': subscription,
        }
    )