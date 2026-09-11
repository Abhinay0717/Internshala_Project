from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from .models import LanguageChangeOTP, UserProfile
from django.core.mail import send_mail
import random


def home(request):

    french_verified = request.session.get(
        'french_verified',
        False
    )

    return render(request, 'home.html', {
        'french_verified': french_verified
    })


def save_language(request):

    if request.method == 'POST':

        language = request.POST.get('language')

        user = User.objects.first()

        if user:

            profile, created = UserProfile.objects.get_or_create(
                user=user
            )

            profile.language = language
            profile.save()

        return redirect('/')

    return redirect('/')


def generate_otp():

    return str(random.randint(100000, 999999))


def send_language_otp(request):

    user = User.objects.first()

    if not user:

        return render(request, 'home.html', {
            'error': 'No registered user found.'
        })

    otp = generate_otp()

    LanguageChangeOTP.objects.create(
        user=user,
        otp=otp
    )

    send_mail(
        'French Language Change OTP',
        f'Your OTP is: {otp}',
        'noreply@internshipportal.com',
        [user.email],
    )

    return render(request, 'verify_otp.html', {
        'message': 'OTP sent successfully.'
    })


def verify_otp(request):

    if request.method == 'POST':

        entered_otp = request.POST.get('otp')

        otp_record = LanguageChangeOTP.objects.filter(
            otp=entered_otp,
            is_verified=False
        ).last()

        if otp_record:

            otp_record.is_verified = True
            otp_record.save()

            request.session['french_verified'] = True

            profile, created = UserProfile.objects.get_or_create(
                user=otp_record.user
            )

            profile.language = 'fr'
            profile.save()

            return redirect('/')

        return render(request, 'verify_otp.html', {
            'message': 'Invalid OTP. Please try again.'
        })

    return render(request, 'verify_otp.html')