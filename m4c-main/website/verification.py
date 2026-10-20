import logging
import json
import secrets
from datetime import timedelta
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.core import signing
from django.core.mail import send_mail
from django.utils import timezone

from .models import MemberProfile, VerificationCode

logger = logging.getLogger(__name__)

CODE_LIFETIME = timedelta(minutes=10)
RESEND_COOLDOWN = timedelta(seconds=60)
MAX_ATTEMPTS = 5
TOKEN_MAX_AGE = 600  # seconds, matches CODE_LIFETIME


class VerificationError(Exception):
    pass


def _email_is_verified(user):
    profile = getattr(user, "member_profile", None)
    return profile is None or profile.email_verified


def _deliver_email(user, code, link):
    if not settings.DEFAULT_FROM_EMAIL:
        raise VerificationError("Email delivery is not configured.")
    body = (
        f"Your M4C email verification code is {code}. It expires in 10 minutes.\n\n"
        f"You can also verify your email by opening this link:\n{link}\n\n"
        f"If you did not create an account with Movement for Change, you can ignore this message."
    )
    if not settings.EMAIL_HOST and settings.EMAIL_BACKEND.endswith("console.EmailBackend"):
        logger.info("Email verification code for %s: %s (link: %s)", user.email, code, link)
        send_mail(
            "Your M4C verification code",
            body,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        return
    if not settings.EMAIL_HOST:
        raise VerificationError("Email delivery is not configured.")
    send_mail(
        "Your M4C verification code",
        body,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )


def _deliver_whatsapp(phone_number, code):
    access_token = settings.WHATSAPP_ACCESS_TOKEN
    phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
    if not access_token or not phone_number_id:
        logger.warning("WhatsApp verification code for %s: %s", phone_number, code)
        return

    url = (
        f"https://graph.facebook.com/{settings.WHATSAPP_GRAPH_API_VERSION}/"
        f"{phone_number_id}/messages"
    )
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number.lstrip("+"),
        "type": "template",
        "template": {
            "name": settings.WHATSAPP_TEMPLATE_NAME,
            "language": {"code": settings.WHATSAPP_TEMPLATE_LANGUAGE},
            "components": [{
                "type": "body",
                "parameters": [{"type": "text", "text": code}],
            }],
        },
    }
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:
            response.read()
    except (HTTPError, URLError, TimeoutError) as exc:
        raise VerificationError("WhatsApp could not send the verification message.") from exc


def _build_link(request, token):
    if request is not None:
        return request.build_absolute_uri(
            f"/verify/email/?token={signing.dumps({'uid': request.user.pk, 'token': token})}"
        )
    site_url = getattr(settings, "SITE_URL", "").rstrip("/")
    path = f"/verify/email/?token={signing.dumps({'uid': 0, 'token': token})}"
    return f"{site_url}{path}" if site_url else path


def issue_verification_code(user, channel, request=None):
    profile = user.member_profile
    if channel == VerificationCode.Channel.EMAIL and profile.email_verified:
        raise VerificationError("This email address is already verified.")
    if channel == VerificationCode.Channel.PHONE and profile.phone_verified:
        raise VerificationError("This phone number is already verified.")
    if channel not in VerificationCode.Channel.values:
        raise VerificationError("Unknown verification channel.")

    now = timezone.now()
    challenge = VerificationCode.objects.filter(user=user, channel=channel).first()
    if challenge and now - challenge.sent_at < RESEND_COOLDOWN:
        raise VerificationError("Please wait a minute before requesting another code.")

    code = f"{secrets.randbelow(1_000_000):06d}"
    defaults = {
        "code_hash": make_password(code),
        "expires_at": now + CODE_LIFETIME,
        "sent_at": now,
        "attempts": 0,
    }
    link = ""
    if channel == VerificationCode.Channel.EMAIL:
        token = secrets.token_urlsafe(32)
        defaults["token_hash"] = make_password(token)
        link = _build_link(request, token)
    else:
        defaults["token_hash"] = ""
    challenge, _ = VerificationCode.objects.update_or_create(
        user=user,
        channel=channel,
        defaults=defaults,
    )
    try:
        if channel == VerificationCode.Channel.EMAIL:
            _deliver_email(user, code, link)
        else:
            _deliver_whatsapp(profile.phone_number, code)
    except Exception as exc:
        logger.warning("Could not send %s verification to user %s", channel, user.pk, exc_info=True)
        challenge.sent_at = now - RESEND_COOLDOWN
        challenge.save(update_fields=("sent_at",))
        if isinstance(exc, VerificationError):
            raise
        raise VerificationError("The verification message could not be sent. Please try again later.") from exc


def verify_email_link(token_value):
    """Verify an email via a signed link token. Returns (ok, message, user_or_none)."""
    try:
        payload = signing.loads(token_value, max_age=TOKEN_MAX_AGE)
    except signing.SignatureExpired:
        return False, "This verification link has expired. Request a new code.", None
    except signing.BadSignature:
        return False, "This verification link is invalid.", None

    user = get_user_model().objects.filter(pk=payload.get("uid")).first()
    if user is None:
        return False, "This verification link is invalid.", None

    profile = getattr(user, "member_profile", None)
    if profile is None:
        return False, "This verification link is invalid.", None
    if profile.email_verified:
        return True, "Your email is already verified.", user

    challenge = VerificationCode.objects.filter(user=user, channel=VerificationCode.Channel.EMAIL).first()
    if challenge is None or not challenge.token_hash or challenge.expires_at <= timezone.now():
        return False, "This verification link has expired. Request a new code.", None

    if not check_password(payload.get("token", ""), challenge.token_hash):
        return False, "This verification link is invalid.", None

    profile.email_verified = True
    profile.save(update_fields=("email_verified",))
    challenge.delete()
    return True, "Your email has been verified. You can sign in now.", user


def verify_code(user, channel, code):
    profile = user.member_profile
    verified_field = "email_verified" if channel == VerificationCode.Channel.EMAIL else "phone_verified"
    if getattr(profile, verified_field):
        return True, "This contact method is already verified."

    challenge = VerificationCode.objects.filter(user=user, channel=channel).first()
    if challenge is None or challenge.expires_at <= timezone.now():
        return False, "That code has expired. Request a new one."
    if challenge.attempts >= MAX_ATTEMPTS:
        return False, "Too many incorrect attempts. Request a new code."

    challenge.attempts += 1
    if not check_password(code.strip(), challenge.code_hash):
        challenge.save(update_fields=("attempts",))
        return False, "That code is incorrect. Check the message and try again."

    setattr(profile, verified_field, True)
    profile.save(update_fields=(verified_field,))
    challenge.delete()
    return True, "Contact method verified."