from io import StringIO
from unittest.mock import patch

from django.contrib.auth import authenticate, get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase


class CreateStaffUserCommandTests(TestCase):
    @patch(
        "submissions.management.commands.create_staff_user.getpass",
        side_effect=["StrongPass123!", "StrongPass123!"],
    )
    def test_creates_staff_account_without_superuser_access(self, _getpass):
        output = StringIO()

        call_command("create_staff_user", "editor", "--email", "editor@example.com", stdout=output)

        user = get_user_model().objects.get(username="editor")
        self.assertTrue(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(user.email, "editor@example.com")
        self.assertIsNotNone(authenticate(username="editor", password="StrongPass123!"))
        self.assertIn("Created staff user 'editor'.", output.getvalue())

    @patch(
        "submissions.management.commands.create_staff_user.getpass",
        side_effect=["StrongPass123!", "different"],
    )
    def test_mismatched_passwords_do_not_create_account(self, _getpass):
        with self.assertRaisesMessage(CommandError, "Passwords do not match"):
            call_command("create_staff_user", "editor")

        self.assertFalse(get_user_model().objects.filter(username="editor").exists())
