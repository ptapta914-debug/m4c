import re

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import MemberProfile


class MemberAuthenticationForm(AuthenticationForm):
    def clean(self):
        identifier = self.cleaned_data.get("username")
        if identifier and "@" in identifier:
            user = get_user_model().objects.filter(email__iexact=identifier).first()
            if user:
                self.cleaned_data["username"] = user.get_username()
        return super().clean()


class MemberCreationForm(UserCreationForm):
    full_name = forms.CharField(
        label="Full name",
        max_length=150,
        widget=forms.TextInput(attrs={"autocomplete": "name"}),
    )
    email = forms.EmailField(
        label="Email address",
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )
    phone_number = forms.CharField(
        label="WhatsApp number",
        max_length=32,
        widget=forms.TelInput(attrs={"autocomplete": "tel", "placeholder": "+254 712 345 678"}),
    )
    county = forms.ChoiceField(choices=(("", "Select county"),))
    interest = forms.ChoiceField(choices=(
        ("", "Select role"),
        ("Community Mobilizer", "Community Mobilizer"),
        ("Youth Leader", "Youth Leader"),
        ("Women Leader", "Women Leader"),
        ("Dialogue Facilitator", "Dialogue Facilitator"),
        ("Faith Leader", "Faith Leader"),
        ("General Volunteer", "General Volunteer"),
        ("Comrades / Campus Volunteer", "Comrades / Campus Volunteer"),
    ))

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username", "email")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email address already exists.")
        return email

    def clean_phone_number(self):
        phone_number = re.sub(r"[^0-9+]", "", self.cleaned_data["phone_number"])
        if phone_number.startswith("00"):
            phone_number = "+" + phone_number[2:]
        elif phone_number.startswith("0"):
            phone_number = "+254" + phone_number[1:]
        elif phone_number.startswith("254"):
            phone_number = "+" + phone_number

        if not re.fullmatch(r"\+[1-9]\d{7,14}", phone_number):
            raise ValidationError("Enter a valid international number, such as +254 712 345 678.")
        if MemberProfile.objects.filter(phone_number=phone_number).exists():
            raise ValidationError("An account with this mobile number already exists.")
        return phone_number

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            self.save_m2m()
            MemberProfile.objects.create(
                user=user,
                full_name=self.cleaned_data["full_name"].strip(),
                phone_number=self.cleaned_data["phone_number"],
                county=self.cleaned_data["county"],
                interest=self.cleaned_data["interest"],
            )
        return user