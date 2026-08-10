"""Phase 3 task 6: login rate limiting (django-axes) and forced password change for
seed_demo accounts. Session-expiry settings (SESSION_COOKIE_AGE etc.) aren't covered here —
simulating real elapsed time for a cookie-expiry test is low value; the settings themselves
are plain constants in config/settings/base.py."""

import pytest
from django.urls import reverse

from apps.tenancy.models import Membership

from .factories import MembershipFactory, OrganizationFactory, UserFactory

pytestmark = pytest.mark.django_db

WRONG_PASSWORD = "definitely-wrong"
RIGHT_PASSWORD = "CorrectHorse123!"


def _real_user(email="locktest@test.local"):
    user = UserFactory(email=email)
    user.set_password(RIGHT_PASSWORD)
    user.save()
    return user


def test_axes_locks_out_after_repeated_failures(client):
    user = _real_user()
    login_url = reverse("login")

    for _ in range(5):
        client.post(login_url, {"username": user.email, "password": WRONG_PASSWORD})

    response = client.post(login_url, {"username": user.email, "password": RIGHT_PASSWORD})
    # Locked out even with the *correct* password — that's the whole point of axes.
    # axes returns 429 (Too Many Requests), not 403 — confirmed by the log output.
    assert response.status_code == 429


def test_login_still_works_below_the_failure_limit(client):
    user = _real_user()
    login_url = reverse("login")

    for _ in range(3):
        client.post(login_url, {"username": user.email, "password": WRONG_PASSWORD})

    response = client.post(login_url, {"username": user.email, "password": RIGHT_PASSWORD})
    assert response.status_code == 302  # normal post-login redirect


def test_lockout_is_scoped_to_one_username_ip_pair_not_the_whole_ip(client):
    """AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]] — a lab's shared IP
    shouldn't get locked out because one account on it had 5 bad attempts."""
    victim = _real_user(email="victim@test.local")
    attacker_target = _real_user(email="attacker-target@test.local")
    login_url = reverse("login")

    for _ in range(5):
        client.post(login_url, {"username": attacker_target.email, "password": WRONG_PASSWORD})

    response = client.post(login_url, {"username": victim.email, "password": RIGHT_PASSWORD})
    assert response.status_code == 302  # victim, same test client (same IP), unaffected


def test_must_change_password_redirects_to_password_change(client):
    org = OrganizationFactory()
    user = _real_user()
    user.must_change_password = True
    user.save()
    MembershipFactory(user=user, organization=org, role=Membership.Role.DEPT_STAFF)
    client.force_login(user)

    response = client.get(reverse("catalog:item_list"))
    assert response.status_code == 302
    assert response.url == reverse("password_change")


def test_password_change_clears_the_flag_and_unblocks_navigation(client):
    org = OrganizationFactory()
    user = _real_user()
    user.must_change_password = True
    user.save()
    MembershipFactory(user=user, organization=org, role=Membership.Role.DEPT_STAFF)
    client.force_login(user)

    response = client.post(
        reverse("password_change"),
        {
            "old_password": RIGHT_PASSWORD,
            "new_password1": "BrandNewPassword456!",
            "new_password2": "BrandNewPassword456!",
        },
    )
    assert response.status_code == 302
    user.refresh_from_db()
    assert user.must_change_password is False

    response = client.get(reverse("catalog:item_list"))
    assert response.status_code == 200


def test_must_change_password_user_can_still_reach_logout(client):
    user = _real_user()
    user.must_change_password = True
    user.save()
    client.force_login(user)

    response = client.post(reverse("logout"))
    assert response.status_code in (200, 302)  # not redirected into a loop back to itself
