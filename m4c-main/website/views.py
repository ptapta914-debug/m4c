import json
import logging
from pathlib import Path

from django.conf import settings
from django.contrib.auth import login
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.http import JsonResponse
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.views.csrf import csrf_failure as default_csrf_failure
from django.views.decorators.http import require_POST

from .forms import MemberCreationForm
from .models import VerificationCode, VolunteerRegistration
from .verification import (
    VerificationError,
    issue_verification_code,
    verify_code,
    verify_email_link,
)

logger = logging.getLogger(__name__)

COUNTIES = [
    "Mombasa", "Kwale", "Kilifi", "Tana River", "Lamu", "Taita-Taveta", "Garissa", "Wajir", "Mandera", "Marsabit",
    "Isiolo", "Meru", "Tharaka-Nithi", "Embu", "Kitui", "Machakos", "Makueni", "Nyandarua", "Nyeri", "Kirinyaga",
    "Murang'a", "Kiambu", "Turkana", "West Pokot", "Samburu", "Trans Nzoia", "Uasin Gishu", "Elgeyo-Marakwet",
    "Nandi", "Baringo", "Laikipia", "Nakuru", "Narok", "Kajiado", "Kericho", "Bomet", "Kakamega", "Vihiga",
    "Bungoma", "Busia", "Siaya", "Kisumu", "Homa Bay", "Migori", "Kisii", "Nyamira", "Nairobi",
]

VALUES = [
    ("Peace", "Promoting peaceful coexistence and non-violent approaches.", "✧", "blue"),
    ("Unity", "Bringing people and communities together around shared aspirations.", "◎", "yellow"),
    ("Integrity", "Upholding honesty, accountability and ethical conduct.", "✓", "green"),
    ("Respect", "Recognizing the dignity, rights and perspectives of every person.", "♡", "red"),
    ("Inclusivity", "Creating space for people from diverse backgrounds to participate.", "◈", "teal"),
    ("Dialogue", "Encouraging communication, listening and constructive engagement.", "↔", "blue"),
    ("Service", "Putting communities and the common good at the heart of our work.", "→", "yellow"),
]

STATS = [
    ("1000+", "Peace Ambassadors", "🕊️"),
    ("47", "Counties Engaged", "🗺️"),
    ("15K+", "Citizens Mobilized", "👥"),
    ("500+", "Community Leaders", "🎯"),
]

NATIONAL_LEADERSHIP = [
    "National Patron", "Deputy Patron", "Secretary", "Mobilization / Organizing",
    "Communications / Digital", "Youth Groups Lead", "Women Groups Lead",
    "Finance / Resources", "Research / Data", "Discipline / Ethics",
    "Special Programmes / Stakeholder Relations",
]

REGIONAL_LEADERSHIP = [
    "Regional Patron", "Deputy Patron", "Secretary", "Mobilization / Organizing",
    "Communications / Digital", "Youth Groups Lead", "Women Groups Lead",
    "Finance / Resources", "Research / Data", "Discipline / Ethics",
    "Special Programmes / Stakeholder Relations",
]

COUNTY_LEADERSHIP = [
    "County Patron", "Deputy Patron", "Secretary", "Mobilization / Organizing",
    "Communications / Digital", "Youth Groups Lead", "Women Groups Lead",
    "Finance / Resources", "Research / Data", "Discipline / Ethics",
    "Special Programmes / Stakeholder Relations",
]

COMRADES_ROLES = [
    "Campus Patron", "Campus Chairperson", "Deputy Chairperson", "Secretary",
    "Organizing Secretary", "Treasurer", "Communications / Digital Lead",
    "Academic & Policy Lead", "Welfare & Inclusion Lead", "Mobilization Team",
    "Class / Department Ambassadors",
]

LEADERSHIP_PROFILES = [
    {
        "image": "images/national-chair-chief.jpeg",
        "name": "",
        "role": "National Chair",
    },
    {
        "image": "images/kimani-w-brian-national-secretary.jpeg",
        "name": "Kimani W. Brian",
        "role": "National Secretary",
    },
    {
        "image": "images/joseph-masini-national-coordinator.jpeg",
        "name": "Joseph Masini",
        "role": "National Coordinator",
    },
    {
        "image": "images/rob-jilo-national-finance-resource-mobilization.jpeg",
        "name": "Rob Jilo",
        "role": "National Finance & Resource Mobilization",
    },
    {
        "image": "images/jared-opiyo-national-operations.jpeg",
        "name": "Jared Opiyo",
        "role": "National Operations",
    },
    {
        "image": "images/muchina-nyaga-national-media-and-communication.jpeg",
        "name": "Muchina Nyaga",
        "role": "National Media & Communication",
    },
    {
        "image": "images/brian-gitonga-embu-county-patron.jpeg",
        "name": "Brian Gitonga",
        "role": "County Patron, Embu",
    },
    {
        "image": "images/esther-muteri-kajiado-county-patron.jpeg",
        "name": "Esther Muteri",
        "role": "County Patron, Kajiado",
    },
    {
        "image": "images/john-waithaka-county-patron-nyeri.jpeg",
        "name": "John Waithaka",
        "role": "County Patron, Nyeri",
    },
    {
        "image": "images/martin-kor-deputy-county-patron-samburu-county.jpeg",
        "name": "Martin Kor",
        "role": "Deputy County Patron, Samburu",
    },
    {
        "image": "images/moses-mwero-county-patron-kwale-county.jpeg",
        "name": "Moses Mwero",
        "role": "County Patron, Kwale",
    },
    {
        "image": "images/wanjeri-esther-stacy-nakuru-county-patron.jpeg",
        "name": "Wanjeri Esther Stacy",
        "role": "County Patron, Nakuru",
    },
]

COUNTY_DIRECTORY_PATH = Path(settings.BASE_DIR) / "static" / "data" / "kenya-county-directory.json"
COUNTY_DIRECTORY = json.loads(COUNTY_DIRECTORY_PATH.read_text(encoding="utf-8"))["counties"]


def make_county_profiles():
    profiles = []
    for county in COUNTIES:
        directory = COUNTY_DIRECTORY[county]
        profiles.append({
            "name": county,
            "slug": directory["slug"],
            "region": "National county network",
            "county_patron": "County Patron to be confirmed",
            "ward_leadership": "Ward leadership structure under development",
            "focus": "Peacebuilding, outreach and mobilization",
            "subcounties": directory["subcounties"],
            "ward_count": sum(len(subcounty["wards"]) for subcounty in directory["subcounties"]),
        })
    return profiles

COUNTY_PROFILES = make_county_profiles()


def home(request):
    return render(request, "index.html", {
        "counties": COUNTIES,
        "values": VALUES,
        "stats": STATS,
    })


def leadership(request):
    return render(request, "leadership.html", {
        "leadership_profiles": LEADERSHIP_PROFILES,
        "national_leadership": NATIONAL_LEADERSHIP,
        "regional_leadership": REGIONAL_LEADERSHIP,
        "county_leadership": COUNTY_LEADERSHIP,
    })


def comrades(request):
    return render(request, "comrades.html", {
        "campus_roles": COMRADES_ROLES,
    })


def counties(request):
    return render(request, "counties.html", {
        "counties": COUNTY_PROFILES,
    })


def county_detail(request, slug):
    county = next((item for item in COUNTY_PROFILES if item["slug"] == slug), None)
    if county is None:
        return render(request, "county_detail.html", {
            "county": {"name": "County", "description": "County profile not yet available."},
        }, status=404)
    return render(request, "county_detail.html", {"county": county})


class MemberLoginView(LoginView):
    template_name = "login.html"

    def form_valid(self, form):
        user = form.get_user()
        profile = getattr(user, "member_profile", None)
        if profile is not None and not profile.email_verified:
            login(self.request, user)
            try:
                issue_verification_code(user, VerificationCode.Channel.EMAIL, self.request)
                messages.info(
                    self.request,
                    "Your email is not verified yet. We sent a fresh code and a verification link to your email.",
                )
            except VerificationError as exc:
                messages.warning(self.request, f"Please verify your email to continue: {exc}")
            return redirect("verify-account")
        return super().form_valid(form)


def verify_email_link_view(request):
    ok, message, user = verify_email_link(request.GET.get("token", ""))
    if ok and user is not None and request.user.is_authenticated and request.user.pk == user.pk:
        messages.success(request, message)
        return redirect("verify-account")
    if ok:
        messages.success(request, message)
        return redirect("login")
    messages.error(request, message)
    return redirect("login")


def register(request):
    if request.user.is_authenticated:
        return redirect("home")

    form = MemberCreationForm(request.POST or None)
    form.fields["county"].choices = [("", "Select county")] + [(county, county) for county in COUNTIES]
    for field_name, autocomplete in (
        ("full_name", "name"),
        ("username", "username"),
        ("email", "email"),
        ("phone_number", "tel"),
        ("password1", "new-password"),
        ("password2", "new-password"),
    ):
        form.fields[field_name].widget.attrs.update({
            "autocomplete": autocomplete,
            "aria-invalid": "true" if form[field_name].errors else "false",
        })

    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        for channel in (VerificationCode.Channel.EMAIL, VerificationCode.Channel.PHONE):
            channel_label = "WhatsApp" if channel == VerificationCode.Channel.PHONE else "email"
            try:
                issue_verification_code(user, channel, request)
                messages.success(request, f"A verification code was sent to your {channel_label}.")
            except VerificationError as exc:
                messages.warning(request, f"Your account is active, but {channel_label} verification could not be sent: {exc}")
        return redirect("verify-account")

    return render(request, "register.html", {"form": form})


@login_required
def verify_account(request):
    profile = request.user.member_profile
    if request.method == "POST":
        channel = request.POST.get("channel", "")
        action = request.POST.get("action", "")
        if channel not in VerificationCode.Channel.values:
            messages.error(request, "Choose a valid verification method.")
        elif action == "verify":
            is_verified, message = verify_code(request.user, channel, request.POST.get("code", ""))
            (messages.success if is_verified else messages.error)(request, message)
        elif action == "resend":
            channel_label = "WhatsApp" if channel == VerificationCode.Channel.PHONE else "email"
            try:
                issue_verification_code(request.user, channel, request)
                messages.success(request, f"A new {channel_label} verification code was sent.")
            except VerificationError as exc:
                messages.error(request, str(exc))
        return redirect("verify-account")

    return render(request, "verify_account.html", {"profile": profile})


@login_required
def profile(request):
    return render(request, "profile.html", {"profile": request.user.member_profile})


def csrf_failure(request, reason=""):
    if request.path == "/api/volunteers":
        return JsonResponse(
            {"message": "Your form security token expired. Reload the page and try again."},
            status=403,
        )
    return default_csrf_failure(request, reason=reason)


@require_POST
def volunteer_registration(request):
    """Validate and persist a public volunteer registration submitted as JSON."""
    try:
        payload = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"message": "Invalid JSON"}, status=400)

    if not isinstance(payload, dict):
        return JsonResponse({"message": "Invalid request body"}, status=400)

    # Accept both the camelCase keys used by older clients and Django-style names.
    aliases = {
        "full_name": ("fullName", "full_name"),
        "phone_number": ("phoneNumber", "phone_number"),
        "county": ("county",),
        "interest": ("interest",),
        "email": ("email",),
    }
    data = {}
    for field, keys in aliases.items():
        value = next((payload.get(key) for key in keys if key in payload), "")
        data[field] = value.strip() if isinstance(value, str) else ""

    if any(not data[field] for field in ("full_name", "phone_number", "county", "interest")):
        return JsonResponse({"message": "Please provide your name, phone number, county and area of interest."}, status=400)
    if len(data["full_name"]) > 150 or len(data["phone_number"]) > 32 or len(data["county"]) > 80 or len(data["interest"]) > 80:
        return JsonResponse({"message": "One or more fields are too long."}, status=400)
    if data["email"]:
        try:
            validate_email(data["email"])
        except ValidationError:
            return JsonResponse({"message": "Please provide a valid email address."}, status=400)

    registration = VolunteerRegistration.objects.create(**data)
    logger.info("Volunteer registration created: id=%s county=%s", registration.pk, registration.county)
    return JsonResponse({
        "message": "Thank you for registering your interest with M4C. Your details have been recorded.",
        "registration_id": registration.pk,
    }, status=201)
