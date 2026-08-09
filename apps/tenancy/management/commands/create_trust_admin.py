import getpass

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create (or promote) a user to Trust Admin — cross-org access, is_staff, is_superuser."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--username", required=False)
        parser.add_argument(
            "--password", required=False, help="If omitted, you'll be prompted (not echoed)."
        )

    def handle(self, *args, **options):
        User = get_user_model()
        email = options["email"]
        username = options["username"] or email.split("@")[0]
        password = options["password"] or getpass.getpass("Password: ")

        user, created = User.objects.get_or_create(
            email=email,
            defaults={"username": username},
        )
        user.is_trust_admin = True
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()

        if not user.username:
            raise CommandError(f"User {email} exists with no username; set one before continuing.")

        verb = "Created" if created else "Promoted existing"
        self.stdout.write(self.style.SUCCESS(f"{verb} trust admin: {email}"))
