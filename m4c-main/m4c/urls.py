from django.contrib import admin
from django.contrib.auth.views import (
    LogoutView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.urls import path

from website import forms, views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", views.MemberLoginView.as_view(authentication_form=forms.MemberAuthenticationForm), name="login"),
    path("verify/email/", views.verify_email_link_view, name="verify-email-link"),
    path("password-reset/", PasswordResetView.as_view(
        template_name="password_reset_form.html",
        email_template_name="password_reset_email.txt",
        subject_template_name="password_reset_subject.txt",
        extra_email_context={"protocol": "https"},
    ), name="password_reset"),
    path("password-reset/sent/", PasswordResetDoneView.as_view(template_name="password_reset_done.html"), name="password_reset_done"),
    path("password-reset/<uidb64>/<token>/", PasswordResetConfirmView.as_view(template_name="password_reset_confirm.html"), name="password_reset_confirm"),
    path("password-reset/complete/", PasswordResetCompleteView.as_view(template_name="password_reset_complete.html"), name="password_reset_complete"),
    path("register/", views.register, name="register"),
    path("verify/", views.verify_account, name="verify-account"),
    path("profile/", views.profile, name="profile"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("", views.home, name="home"),
    path("leadership/", views.leadership, name="leadership"),
    path("comrades/", views.comrades, name="comrades"),
    path("counties/", views.counties, name="counties"),
    path("counties/<slug:slug>/", views.county_detail, name="county-detail"),
    path("api/volunteers", views.volunteer_registration, name="volunteer-registration"),
]
