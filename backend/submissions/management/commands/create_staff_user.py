from getpass import getpass

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create a staff user for the submission dashboard."

    def add_arguments(self, parser):
        parser.add_argument("username", help="Username for the new staff account")
        parser.add_argument("--email", default="", help="Email address (optional)")

    def handle(self, *args, **options):
        user_model = get_user_model()
        username = user_model.normalize_username(options["username"].strip())
        email = options["email"].strip()

        if not username:
            raise CommandError("Username cannot be empty.")
        if user_model.objects.filter(username=username).exists():
            raise CommandError(f"User {username!r} already exists.")

        password = getpass("Password: ")
        if password != getpass("Password (again): "):
            raise CommandError("Passwords do not match.")

        user = user_model(username=username, email=email, is_staff=True)
        try:
            validate_password(password, user=user)
            user.set_password(password)
            user.full_clean()
        except ValidationError as error:
            raise CommandError(" ".join(error.messages)) from error

        user.save()
        self.stdout.write(self.style.SUCCESS(f"Created staff user {username!r}."))
