from django.urls import path
from .views import (
    home,
    register,
    user_login,
    verify_login_otp,
    change_password,
    send_language_otp,
    verify_otp,
    forgot_password,
    verify_password_reset_otp,
    complete_password_reset,
    login_history,
    active_sessions,
    logout_other_devices,
    profile,
)

urlpatterns = [

    # ======================================================
    # HOME
    # ======================================================

    path(
        '',
        home,
        name='home'
    ),


    # ======================================================
    # REGISTER
    # ======================================================

    path(
        'register/',
        register,
        name='register'
    ),


    # ======================================================
    # LOGIN
    # ======================================================

    path(
        'login/',
        user_login,
        name='login'
    ),

    path(
        'verify-login-otp/',
        verify_login_otp,
        name='verify_login_otp'
    ),


    # ======================================================
    # CHANGE PASSWORD
    # ======================================================

    path(
        'change-password/',
        change_password,
        name='change_password'
    ),


    # ======================================================
    # LANGUAGE OTP
    # ======================================================

    path(
        'send-language-otp/',
        send_language_otp,
        name='send_language_otp'
    ),

    path(
        'verify-otp/',
        verify_otp,
        name='verify_otp'
    ),


    # ======================================================
    # FORGOT PASSWORD
    # ======================================================

    path(
        'forgot-password/',
        forgot_password,
        name='forgot_password'
    ),

    path(
        'verify-password-reset-otp/',
        verify_password_reset_otp,
        name='verify_password_reset_otp'
    ),

    path(
        'complete-password-reset/',
        complete_password_reset,
        name='complete_password_reset'
    ),


    # ======================================================
    # LOGIN HISTORY
    # ======================================================

    path(
        'login-history/',
        login_history,
        name='login_history'
    ),


    # ======================================================
    # ACTIVE SESSIONS
    # ======================================================

    path(
        'active-sessions/',
        active_sessions,
        name='active_sessions'
    ),

    path(
        'logout-other-devices/',
        logout_other_devices,
        name='logout_other_devices'
    ),


    # ======================================================
    # PROFILE
    # ======================================================

    path(
        'profile/',
        profile,
        name='profile'
    ),

]