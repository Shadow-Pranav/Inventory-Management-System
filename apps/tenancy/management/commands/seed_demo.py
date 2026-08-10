from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.tenancy.models import Department, Membership, Organization

DEMO_PASSWORD = "DemoPass123!"

DEMO_ORG_SLUGS = ["cet", "ims"]

DEMO_DEPARTMENTS = [
    {"name": "Stores", "code": "STORES"},
    {"name": "Administration", "code": "ADMIN"},
]

DEMO_ROLES = [
    Membership.Role.ORG_ADMIN,
    Membership.Role.STORE_MANAGER,
    Membership.Role.DEPT_STAFF,
    Membership.Role.AUDITOR,
]


class Command(BaseCommand):
    help = (
        "Seed demo departments and one user per role in a couple of organizations. "
        "Local/dev use only — never run against a real Trust database."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        logins = [self._seed_trust_admin(User)]

        for slug in DEMO_ORG_SLUGS:
            try:
                org = Organization.objects.get(slug=slug)
            except Organization.DoesNotExist:
                self.stderr.write(self.style.WARNING(f"Organization '{slug}' not found — skipping"))
                continue
            logins += self._seed_org(User, org)

        self.stdout.write(
            self.style.SUCCESS(f"Seeded demo data. Password for every login: {DEMO_PASSWORD}")
        )
        for email, role, org_name in logins:
            self.stdout.write(f"  {email:35s} {role:15s} {org_name}")

    def _seed_trust_admin(self, User):
        email = "trustadmin@sits.local"
        user, _ = User.objects.get_or_create(email=email, defaults={"username": "trustadmin"})
        user.set_password(DEMO_PASSWORD)
        user.is_trust_admin = True
        user.is_staff = True
        user.must_change_password = True  # shared public password — force a change on login
        user.save()
        return (email, "TRUST_ADMIN", "—")

    def _seed_org(self, User, org):
        departments = []
        for dept in DEMO_DEPARTMENTS:
            department, _ = Department.all_objects.get_or_create(
                organization=org, code=dept["code"], defaults={"name": dept["name"]}
            )
            departments.append(department)

        logins = []
        for role in DEMO_ROLES:
            email = f"{role.lower()}@{org.slug}.sits.local"
            username = f"{org.slug}-{role.lower()}"
            user, _ = User.objects.get_or_create(email=email, defaults={"username": username})
            user.set_password(DEMO_PASSWORD)
            user.must_change_password = True  # shared public password — force a change on login
            user.save()

            department = departments[0] if role == Membership.Role.DEPT_STAFF else None
            Membership.objects.update_or_create(
                user=user,
                organization=org,
                defaults={"role": role, "department": department, "is_active": True},
            )
            logins.append((email, role, org.short_name))
        return logins
