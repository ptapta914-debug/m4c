from django.shortcuts import redirect

# Account routes an unverified-email member may not reach; they are sent to
# the verification page instead. Public pages stay open to everyone.
GATED_URL_NAMES = frozenset({"profile"})


class EmailVerificationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            profile = getattr(user, "member_profile", None)
            if profile is not None and not profile.email_verified:
                resolver_match = getattr(request, "resolver_match", None)
                url_name = getattr(resolver_match, "url_name", "") if resolver_match else ""
                if url_name in GATED_URL_NAMES:
                    return redirect("verify-account")
        return self.get_response(request)
