from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


def send_password_setup_email(request, user):
    """Used for org-admin invites, not the self-service 'forgot password' flow.

    Django's built-in `PasswordResetForm.save()` deliberately skips any user without a
    usable password (`get_users()` filters on `has_usable_password()`) — exactly right for
    "forgot password", exactly wrong here: a freshly invited user *always* has an unusable
    password (`member_invite` sets one on creation) and still needs the email. Builds the
    same token/link `PasswordResetConfirmView` expects, by hand.
    """
    site = get_current_site(request)
    context = {
        "email": user.email,
        "domain": site.domain,
        "site_name": site.name,
        "uid": urlsafe_base64_encode(force_bytes(user.pk)),
        "user": user,
        "token": default_token_generator.make_token(user),
        "protocol": "https" if request.is_secure() else "http",
    }
    subject = "".join(
        render_to_string("registration/password_reset_subject.txt", context).splitlines()
    )
    body = render_to_string("registration/password_reset_email.html", context)
    send_mail(subject, body, None, [user.email])
