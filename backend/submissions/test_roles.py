from importlib import import_module
from types import SimpleNamespace
from unittest.mock import patch

from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from rest_framework.test import APIClient

from submissions.models import Submission


class StaffRoleTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="reviewer", password="ExamplePass123!", is_staff=True
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_new_staff_gets_manager_permissions_by_default(self):
        self.assertTrue(self.user.groups.filter(name="Submission Managers").exists())
        self.assertTrue(self.user.has_perm("submissions.delete_submission"))
        self.assertTrue(self.user.has_perm("submissions.export_all_submissions"))
        session = self.client.get("/api/auth/session/")
        self.assertTrue(session.data["user"]["can_delete_submissions"])
        self.assertTrue(session.data["user"]["can_export_all_submissions"])

    def test_promoted_staff_gets_manager_permissions_by_default(self):
        promoted = get_user_model().objects.create_user(username="promoted", is_staff=False)
        promoted.is_staff = True
        promoted.save(update_fields=["is_staff"])

        self.assertTrue(promoted.groups.filter(name="Submission Managers").exists())
        self.assertTrue(promoted.has_perm("submissions.delete_submission"))
        self.assertTrue(promoted.has_perm("submissions.export_all_submissions"))

    def test_migration_grants_role_to_existing_staff(self):
        old_user = get_user_model().objects.create_user(username="old-staff", is_staff=False)
        get_user_model().objects.filter(pk=old_user.pk).update(is_staff=True)
        self.assertFalse(old_user.groups.filter(name="Submission Managers").exists())

        migration = import_module("submissions.migrations.0018_staff_manager_role")
        migration.grant_existing_staff_manager_role(
            apps, SimpleNamespace(connection=connection)
        )

        old_user.refresh_from_db()
        self.assertTrue(old_user.groups.filter(name="Submission Managers").exists())
        self.assertTrue(old_user.has_perm("submissions.delete_submission"))
        self.assertTrue(old_user.has_perm("submissions.export_all_submissions"))

    def test_reviewer_without_manager_role_can_review_but_not_delete_or_export_all(self):
        self.user.groups.clear()
        self.user.save(update_fields=["email"])
        self.assertFalse(self.user.groups.filter(name="Submission Managers").exists())
        self.user = get_user_model().objects.get(pk=self.user.pk)
        self.client.force_authenticate(self.user)
        submission = Submission.objects.create(
            title="Private Piece",
            submission_type="poetry",
            artist_name="Example Artist",
            pronouns="they/them",
            short_bio="An example artist biography.",
            email="artist@example.com",
            country_origin="DK",
            countries_residence=["DK"],
        )

        self.assertEqual(self.client.get("/api/submissions/").status_code, 200)
        self.assertEqual(self.client.delete(f"/api/submissions/{submission.pk}/").status_code, 403)
        self.assertTrue(Submission.objects.filter(pk=submission.pk).exists())
        with patch("submissions.api.downloads._build_complete_download_zip") as archive:
            self.assertEqual(self.client.get("/api/downloads/complete/").status_code, 403)
            archive.assert_not_called()
        with patch("submissions.api.downloads._build_excel_workbook") as workbook:
            self.assertEqual(self.client.get("/api/downloads/excel/").status_code, 403)
            workbook.assert_not_called()
        session = self.client.get("/api/auth/session/")
        self.assertFalse(session.data["user"]["can_delete_submissions"])
        self.assertFalse(session.data["user"]["can_export_all_submissions"])
