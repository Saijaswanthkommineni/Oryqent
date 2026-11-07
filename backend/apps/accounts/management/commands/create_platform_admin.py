import getpass
import os

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User


class Command(BaseCommand):
    help = "Create an ORYQENT platform administrator without exposing the password in argv."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--full-name", required=True)

    def handle(self, *args, **options):
        email = options["email"].strip().casefold()
        full_name = options["full_name"].strip()
        if not full_name:
            raise CommandError("--full-name cannot be empty.")
        if User.objects.filter(email__iexact=email).exists():
            raise CommandError(f"A user with email {email!r} already exists.")

        password = os.getenv("ORYQENT_PLATFORM_ADMIN_PASSWORD")
        if not password:
            if not os.isatty(0):
                raise CommandError(
                    "Set ORYQENT_PLATFORM_ADMIN_PASSWORD for non-interactive execution."
                )
            password = getpass.getpass("Password: ")
            confirmation = getpass.getpass("Password (again): ")
            if password != confirmation:
                raise CommandError("Passwords do not match.")

        candidate = User(email=email, full_name=full_name)
        try:
            validate_password(password, user=candidate)
        except ValidationError as exc:
            raise CommandError("Password validation failed: " + "; ".join(exc.messages)) from exc

        user = User.objects.create_superuser(email=email, password=password, full_name=full_name)
        self.stdout.write(
            self.style.SUCCESS(f"Created platform administrator {user.email} ({user.id}).")
        )
