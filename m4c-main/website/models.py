from django.conf import settings
from django.db import models
from django.utils import timezone


class MemberProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="member_profile")
    full_name = models.CharField(max_length=150, blank=True, default="")
    phone_number = models.CharField(max_length=16, unique=True)
    county = models.CharField(max_length=80, blank=True, default="")
    interest = models.CharField(max_length=80, blank=True, default="")
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.user.get_username()


class VerificationCode(models.Model):
    class Channel(models.TextChoices):
        EMAIL = "email", "Email"
        PHONE = "phone", "Phone"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="verification_codes")
    channel = models.CharField(max_length=8, choices=Channel.choices)
    code_hash = models.CharField(max_length=128)
    token_hash = models.CharField(max_length=128, blank=True, default="")
    expires_at = models.DateTimeField()
    sent_at = models.DateTimeField(default=timezone.now)
    attempts = models.PositiveSmallIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("user", "channel"), name="unique_user_verification_channel"),
        ]

class VolunteerRegistration(models.Model):
    full_name = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=32)
    county = models.CharField(max_length=80)
    interest = models.CharField(max_length=80)
    email = models.EmailField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.full_name} ({self.county})"
