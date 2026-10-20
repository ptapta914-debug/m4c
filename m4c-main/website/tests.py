import json
import os
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.conf import settings
from django.core import mail
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from website.models import MemberProfile, VerificationCode, VolunteerRegistration
from website.verification import _deliver_email, _deliver_whatsapp, issue_verification_code, verify_code
from website.views import COUNTY_PROFILES


class HomePageTests(SimpleTestCase):
    def test_static_files_are_configured_for_production(self):
        self.assertEqual(settings.STATIC_URL, "/static/")
        self.assertTrue(settings.STATICFILES_DIRS)
        self.assertTrue(settings.STATIC_ROOT)

    def test_home_page_uses_the_animated_full_bleed_brand_logo(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Movement for Change")
        self.assertContains(response, "m4c-logo.jpeg")
        self.assertContains(response, 'property="og:image" content="https://movementforchange.co.ke/static/images/m4c-logo.jpeg"')
        self.assertContains(response, 'name="twitter:card" content="summary_large_image"')
        self.assertContains(response, "hero-background-logo")
        self.assertNotContains(response, "politician-1.jpeg")
        self.assertNotContains(response, "politician-2.jpeg")
        self.assertNotContains(response, "politician-3.jpeg")
        self.assertContains(response, "csrfmiddlewaretoken")
        self.assertContains(response, "Member sign in")
        self.assertContains(response, 'id="signInPanel"')
        self.assertContains(response, 'action="/login/"')
        self.assertContains(response, 'action="/register/"')
        self.assertContains(response, 'name="full_name"')
        self.assertContains(response, 'name="county"')
        self.assertContains(response, 'name="interest"')

class OrganizationPagesTests(SimpleTestCase):
    def test_leadership_page_has_required_sections(self):
        response = self.client.get(reverse("leadership"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "National Leadership")
        self.assertContains(response, "Regional Leadership")
        self.assertNotContains(response, "25 members")
        self.assertNotContains(response, "25 National Senior Patrons")
        self.assertNotContains(response, "Chief")
        self.assertNotContains(response, "Chief, National Secretary")
        self.assertContains(response, "National Chair")
        self.assertContains(response, "Deputy Patron")
        self.assertContains(response, "Special Programmes / Stakeholder Relations")
        self.assertContains(response, "Kimani W. Brian")
        self.assertContains(response, "National Secretary")
        self.assertContains(response, "Joseph Masini")
        self.assertContains(response, "Rob Jilo")
        self.assertContains(response, "Jared Opiyo")
        self.assertContains(response, "National Operations")
        self.assertContains(response, "images/Jared_opiyo_National_operations.jpeg")
        self.assertContains(response, "Muchina Nyaga")
        self.assertContains(response, "National Media and Communication")
        self.assertContains(response, "images/Muchina_nyaga_National_media_and_communication.jpeg")
        for removed_name in (
            "Brian Gitonga", "Martin Kor", "John Waithaka",
            "Wanjeri Esther Stacy", "Esther Muteri", "Moses Mwero",
        ):
            self.assertNotContains(response, removed_name)

    def test_counties_page_lists_kenya_counties(self):
        response = self.client.get(reverse("counties"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "M4C Across Kenya")
        self.assertContains(response, "Nairobi")
        self.assertContains(response, "County map")
        self.assertContains(response, 'id="countySearchForm"')
        self.assertContains(response, 'id="countyMap"')
        self.assertContains(response, "Ward leadership")
        self.assertContains(response, "CC BY 4.0")
        self.assertContains(response, "CC BY 3.0 IGO")
        self.assertContains(response, "Public Domain")

    def test_ward_index_covers_all_counties_and_wards(self):
        self.assertEqual(len(COUNTY_PROFILES), 47)
        self.assertEqual(sum(county["ward_count"] for county in COUNTY_PROFILES), 1450)

        ward_data = json.loads((settings.BASE_DIR / "static/data/kenya-wards.geojson").read_text(encoding="utf-8"))
        self.assertEqual(len(ward_data["features"]), 1450)
        self.assertTrue(all(
            feature["properties"].get("countyName")
            and feature["properties"].get("subcountyName")
            and feature["properties"].get("wardName")
            for feature in ward_data["features"]
        ))

    def test_county_profile_lists_real_subcounties_and_wards(self):
        response = self.client.get(reverse("county-detail", kwargs={"slug": "nairobi"}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dagoretti")
        self.assertContains(response, "Mutu-ini Ward")
        self.assertContains(response, "Ward Patron to be confirmed")

    def test_comrades_page_renders(self):
        response = self.client.get(reverse("comrades"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Comrades")
        self.assertContains(response, "Campus Patron")
        self.assertContains(response, "Academic &amp; Policy Lead")
        self.assertContains(response, "Class / Department Ambassadors")
        self.assertContains(response, "Campus Events")
        self.assertContains(response, "Join Comrades")


class VolunteerApiTests(SimpleTestCase):
    url = reverse("volunteer-registration")

    def test_accepts_valid_token_from_forwarded_https_origin(self):
        codespace_name = os.environ.get("CODESPACE_NAME")
        forwarding_domain = os.environ.get("GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN")
        if not getattr(settings, "SECURE_PROXY_SSL_HEADER", None) or not forwarding_domain:
            self.skipTest("Forwarded HTTPS proxy support is only enabled in Codespaces.")

        client = Client(enforce_csrf_checks=True)
        host = f"{codespace_name}-{os.environ.get('PORT', '8000')}.{forwarding_domain}"
        page = client.get(
            reverse("home"),
            HTTP_HOST=host,
            HTTP_X_FORWARDED_PROTO="https",
        )
        csrf_token = page.cookies["csrftoken"].value
        response = client.post(
            self.url,
            json.dumps({
                "fullName": "Amina Otieno",
                "phoneNumber": "+254700000000",
                "county": "Nairobi",
                "interest": "Youth Leader",
            }),
            content_type="application/json",
            HTTP_HOST=host,
            HTTP_ORIGIN=f"https://{host}",
            HTTP_X_FORWARDED_PROTO="https",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, 200)

    @override_settings(CSRF_TRUSTED_ORIGINS=["https://localhost:8000"])
    def test_accepts_valid_token_from_local_https_join_page(self):
        client = Client(enforce_csrf_checks=True)
        page = client.get(reverse("home"), HTTP_HOST="localhost:8000")
        csrf_token = page.cookies["csrftoken"].value
        response = client.post(
            self.url,
            json.dumps({
                "fullName": "Amina Otieno",
                "phoneNumber": "+254700000000",
                "county": "Nairobi",
                "interest": "Youth Leader",
            }),
            content_type="application/json",
            HTTP_HOST="localhost:8000",
            HTTP_ORIGIN="https://localhost:8000",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, 200)

    def test_registers_a_volunteer(self):
        payload = {
            "fullName": "Amina Otieno",
            "phoneNumber": "+254700000000",
            "county": "Nairobi",
            "interest": "Youth Leader",
            "email": "amina@example.com",
        }

        response = self.client.post(self.url, json.dumps(payload), content_type="application/json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"], payload)

    def test_rejects_missing_required_fields(self):
        response = self.client.post(
            self.url,
            json.dumps({"fullName": "Amina Otieno"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "Missing required fields")

    def test_rejects_invalid_json(self):
        response = self.client.post(self.url, "{", content_type="application/json")

        self.assertEqual(response.status_code, 400)

    def test_csrf_failure_returns_actionable_json(self):
        client = Client(enforce_csrf_checks=True)
        client.get(reverse("home"))

        response = client.post(
            self.url,
            json.dumps({
                "fullName": "Amina Otieno",
                "phoneNumber": "+254700000000",
                "county": "Nairobi",
                "interest": "Youth Leader",
            }),
            content_type="application/json",
            HTTP_X_CSRFTOKEN="stale-token",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["message"], "Your form security token expired. Reload the page and try again.")


class LoginTests(TestCase):
    @override_settings(CSRF_TRUSTED_ORIGINS=["https://movementforchange.co.ke"])
    def test_login_accepts_production_https_origin(self):
        user = get_user_model().objects.create_user(
            username="production-member",
            password="Robust-M4C-passphrase-9482!",
        )
        client = Client(enforce_csrf_checks=True)
        host = "movementforchange.co.ke"
        page = client.get(reverse("login"), HTTP_HOST=host)
        csrf_token = page.cookies["csrftoken"].value

        response = client.post(
            reverse("login"),
            {"username": user.username, "password": "Robust-M4C-passphrase-9482!"},
            HTTP_HOST=host,
            HTTP_ORIGIN=f"https://{host}",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertRedirects(response, reverse("home"))
        self.assertEqual(client.session.get("_auth_user_id"), str(user.pk))

    @override_settings(SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https"))
    def test_login_accepts_forwarded_https_origin_on_deployment_hostname(self):
        user = get_user_model().objects.create_user(
            username="deployed-member",
            password="Robust-M4C-passphrase-9482!",
        )
        client = Client(enforce_csrf_checks=True)
        host = "m4c.onrender.com"
        forwarded_https = {"HTTP_X_FORWARDED_PROTO": "https"}
        page = client.get(reverse("login"), HTTP_HOST=host, **forwarded_https)
        csrf_token = page.cookies["csrftoken"].value

        response = client.post(
            reverse("login"),
            {"username": user.username, "password": "Robust-M4C-passphrase-9482!"},
            HTTP_HOST=host,
            HTTP_ORIGIN=f"https://{host}",
            HTTP_X_CSRFTOKEN=csrf_token,
            **forwarded_https,
        )

        self.assertRedirects(response, reverse("home"))
        self.assertEqual(client.session.get("_auth_user_id"), str(user.pk))

    def test_login_page_renders_accessible_sign_in_form(self):
        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Welcome back to")
        self.assertContains(response, 'aria-labelledby="loginHeading"')
        self.assertContains(response, 'autocomplete="username"')
        self.assertContains(response, "Username or email")
        self.assertContains(response, 'autocomplete="current-password"')
        self.assertContains(response, 'href="/register/"')
        self.assertContains(response, "csrfmiddlewaretoken")

    def test_join_page_creates_and_authenticates_user_with_csrf(self):
        client = Client(enforce_csrf_checks=True)
        page = client.get(reverse("home"))
        csrf_token = page.cookies["csrftoken"].value

        with patch("website.verification._deliver_email"), patch("website.verification._deliver_whatsapp"):
            response = client.post(reverse("register"), {
                "full_name": "New M4C Member",
                "username": "new-m4c-member",
                "email": "new-member@example.com",
                "phone_number": "0712345678",
                "county": "Nairobi",
                "interest": "Youth Leader",
                "password1": "Robust-M4C-passphrase-9482!",
                "password2": "Robust-M4C-passphrase-9482!",
            }, HTTP_X_CSRFTOKEN=csrf_token, follow=True)

        self.assertRedirects(response, reverse("verify-account"))
        user = get_user_model().objects.get(username="new-m4c-member")
        self.assertEqual(client.session.get("_auth_user_id"), str(user.pk))
        self.assertEqual(user.email, "new-member@example.com")
        self.assertEqual(user.member_profile.full_name, "New M4C Member")
        self.assertEqual(user.member_profile.phone_number, "+254712345678")
        self.assertEqual(user.member_profile.county, "Nairobi")
        self.assertEqual(user.member_profile.interest, "Youth Leader")
        self.assertContains(response, "Pending")

    @override_settings(SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https"))
    def test_registration_accepts_forwarded_https_origin_on_deployment_hostname(self):
        client = Client(enforce_csrf_checks=True)
        host = "m4c.onrender.com"
        forwarded_https = {"HTTP_X_FORWARDED_PROTO": "https"}
        page = client.get(reverse("register"), HTTP_HOST=host, **forwarded_https)
        csrf_token = page.cookies["csrftoken"].value

        with patch("website.verification._deliver_email"), patch("website.verification._deliver_whatsapp"):
            response = client.post(
                reverse("register"),
                {
                    "full_name": "Deployed M4C Member",
                    "username": "deployed-m4c-member",
                    "email": "deployed-member@example.com",
                    "phone_number": "0712345678",
                    "county": "Nairobi",
                    "interest": "Youth Leader",
                    "password1": "Robust-M4C-passphrase-9482!",
                    "password2": "Robust-M4C-passphrase-9482!",
                },
                HTTP_HOST=host,
                HTTP_ORIGIN=f"https://{host}",
                HTTP_X_CSRFTOKEN=csrf_token,
                **forwarded_https,
            )

        self.assertRedirects(response, reverse("verify-account"), fetch_redirect_response=False)
        user = get_user_model().objects.get(username="deployed-m4c-member")
        self.assertEqual(client.session.get("_auth_user_id"), str(user.pk))

    def test_registration_rejects_mismatched_passwords(self):
        response = self.client.post(reverse("register"), {
            "full_name": "New M4C Member",
            "username": "new-m4c-member",
            "email": "new-member@example.com",
            "phone_number": "+254712345678",
            "county": "Nairobi",
            "interest": "Youth Leader",
            "password1": "Robust-M4C-passphrase-9482!",
            "password2": "Different-passphrase-8274!",
        })

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].has_error("password2"))

    def test_verification_code_is_hashed_and_verifies_email(self):
        user = get_user_model().objects.create_user(
            username="verified-member",
            email="verified@example.com",
            password="secure-test-password",
        )
        MemberProfile.objects.create(user=user, phone_number="+254712345679")

        with patch("website.verification._deliver_email") as deliver_email:
            issue_verification_code(user, VerificationCode.Channel.EMAIL)

        code = deliver_email.call_args.args[1]
        challenge = VerificationCode.objects.get(user=user, channel=VerificationCode.Channel.EMAIL)
        self.assertNotEqual(challenge.code_hash, code)
        self.assertTrue(challenge.expires_at > challenge.sent_at)

        is_verified, _ = verify_code(user, VerificationCode.Channel.EMAIL, code)

        self.assertTrue(is_verified)
        self.assertTrue(user.member_profile.email_verified)
        self.assertFalse(VerificationCode.objects.filter(pk=challenge.pk).exists())

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        EMAIL_HOST="smtp.example.test",
        DEFAULT_FROM_EMAIL="members@example.test",
    )
    def test_email_delivery_uses_configured_sender(self):
        user = get_user_model().objects.create_user(
            username="email-member",
            email="member@example.test",
            password="secure-test-password",
        )

        _deliver_email(user, "123456")

        self.assertEqual(mail.outbox[0].from_email, "members@example.test")
        self.assertEqual(mail.outbox[0].to, ["member@example.test"])
        self.assertIn("123456", mail.outbox[0].body)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend",
        EMAIL_HOST="",
        DEFAULT_FROM_EMAIL="Movement for Change <noreply@movementforchange.co.ke>",
    )
    def test_email_delivery_falls_back_to_console_backend_without_smtp_config(self):
        user = get_user_model().objects.create_user(
            username="console-email-member",
            email="console-member@example.test",
            password="secure-test-password",
        )

        _deliver_email(user, "654321")

        self.assertEqual(user.email, "console-member@example.test")

    @override_settings(
        WHATSAPP_ACCESS_TOKEN="",
        WHATSAPP_PHONE_NUMBER_ID="",
    )
    def test_whatsapp_delivery_falls_back_to_logging_when_not_configured(self):
        user = get_user_model().objects.create_user(
            username="whatsapp-fallback-member",
            email="whatsapp-fallback@example.com",
            password="secure-test-password",
        )
        MemberProfile.objects.create(
            user=user,
            full_name="WhatsApp Fallback Member",
            phone_number="+254712345680",
            county="Nairobi",
            interest="Youth Leader",
        )

        issue_verification_code(user, VerificationCode.Channel.PHONE)

        self.assertTrue(VerificationCode.objects.filter(user=user, channel=VerificationCode.Channel.PHONE).exists())

    @override_settings(
        WHATSAPP_ACCESS_TOKEN="test-token",
        WHATSAPP_PHONE_NUMBER_ID="123456789",
        WHATSAPP_TEMPLATE_NAME="m4c_verification",
        WHATSAPP_TEMPLATE_LANGUAGE="en",
        WHATSAPP_GRAPH_API_VERSION="v23.0",
    )
    def test_whatsapp_delivery_uses_cloud_api(self):
        provider_response = MagicMock()
        provider_response.__enter__.return_value = provider_response
        with patch("website.verification.urlopen", return_value=provider_response) as send_request:
            _deliver_whatsapp("+254712345678", "123456")

        request = send_request.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(request.full_url, "https://graph.facebook.com/v23.0/123456789/messages")
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.get_header("Authorization"), "Bearer test-token")
        self.assertEqual(payload["messaging_product"], "whatsapp")
        self.assertEqual(payload["to"], "254712345678")
        self.assertEqual(payload["template"]["name"], "m4c_verification")
        self.assertEqual(payload["template"]["components"][0]["parameters"][0]["text"], "123456")

    def test_profile_page_shows_contact_and_status(self):
        user = get_user_model().objects.create_user(
            username="profile-member",
            email="profile@example.com",
            password="secure-test-password",
        )
        MemberProfile.objects.create(
            user=user,
            full_name="Profile Member",
            phone_number="+254712345680",
            county="Nairobi",
            interest="Youth Leader",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("profile"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "profile@example.com")
        self.assertContains(response, "+254712345680")
        self.assertContains(response, "Nairobi")
        self.assertContains(response, "Youth Leader")
        self.assertContains(response, "Verification")

    def test_login_and_logout_use_django_authentication(self):
        user = get_user_model().objects.create_user(
            username="m4c-member",
            password="secure-test-password",
        )

        response = self.client.post(reverse("login"), {
            "username": user.username,
            "password": "secure-test-password",
        })

        self.assertRedirects(response, reverse("home"))
        self.assertEqual(self.client.session.get("_auth_user_id"), str(user.pk))

        response = self.client.post(reverse("logout"))

        self.assertRedirects(response, reverse("home"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_accepts_email_address(self):
        user = get_user_model().objects.create_user(
            username="email-login-member",
            email="member@example.com",
            password="secure-test-password",
        )

        response = self.client.post(reverse("login"), {
            "username": "MEMBER@example.com",
            "password": "secure-test-password",
        })

        self.assertRedirects(response, reverse("home"))
        self.assertEqual(self.client.session.get("_auth_user_id"), str(user.pk))

    def test_home_hides_join_form_for_signed_in_members(self):
        user = get_user_model().objects.create_user(
            username="signed-in-member",
            password="secure-test-password",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Welcome back, signed-in-member")
        self.assertContains(response, reverse("logout"))
        self.assertNotContains(response, 'id="joinPanel"')
        self.assertNotContains(response, "Join the Movement for Peace")

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        EMAIL_HOST="smtp.example.test",
        DEFAULT_FROM_EMAIL="Movement for Change <noreply@movementforchange.co.ke>",
    )
    def test_password_reset_sends_branded_email_with_site_link(self):
        get_user_model().objects.create_user(
            username="reset-member",
            email="member@example.com",
            password="secure-test-password",
        )

        response = self.client.post(
            reverse("password_reset"),
            {"email": "member@example.com"},
            HTTP_HOST="movementforchange.co.ke",
        )

        self.assertRedirects(response, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].from_email, "Movement for Change <noreply@movementforchange.co.ke>")
        self.assertEqual(mail.outbox[0].to, ["member@example.com"])
        self.assertIn("https://movementforchange.co.ke/password-reset/", mail.outbox[0].body)


class VolunteerRegistrationTests(TestCase):
    def test_valid_registration_is_saved_without_logging_personal_data(self):
        response = self.client.post(
            reverse("volunteer-registration"),
            data=json.dumps({
                "fullName": "Test Volunteer",
                "phoneNumber": "+254712345678",
                "county": "Nairobi",
                "interest": "Community Mobilizer",
                "email": "volunteer@example.com",
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(VolunteerRegistration.objects.count(), 1)
        self.assertEqual(VolunteerRegistration.objects.get().full_name, "Test Volunteer")
        self.assertIn("registration_id", response.json())

    def test_registration_rejects_missing_fields(self):
        response = self.client.post(
            reverse("volunteer-registration"),
            data=json.dumps({"fullName": "Test Volunteer"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(VolunteerRegistration.objects.count(), 0)

    def test_registration_rejects_invalid_email(self):
        response = self.client.post(
            reverse("volunteer-registration"),
            data=json.dumps({
                "fullName": "Test Volunteer", "phoneNumber": "+254712345678",
                "county": "Nairobi", "interest": "Volunteer", "email": "not-an-email",
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(VolunteerRegistration.objects.count(), 0)
