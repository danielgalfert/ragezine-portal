from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core import mail
from django.test import TestCase
from django.test import override_settings
from django.conf import settings
from openpyxl import load_workbook
from rest_framework import status
from rest_framework.test import APIClient
from io import BytesIO
from zipfile import ZipFile

from submissions.api.email import send_submission_emails
from submissions.models import Submission, SubmissionText, SubmissionVisual


class AuthenticationEndpointsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username="editor",
            password="S3cretPass123",
        )

    def test_login_session_and_logout_flow(self):
        login_response = self.client.post(
            "/api/auth/login/",
            {"username": "editor", "password": "S3cretPass123"},
            format="json",
        )

        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertEqual(login_response.data["user"]["username"], self.user.username)

        session_response = self.client.get("/api/auth/session/")
        self.assertEqual(session_response.status_code, status.HTTP_200_OK)
        self.assertTrue(session_response.data["authenticated"])

        logout_response = self.client.post("/api/auth/logout/")
        self.assertEqual(logout_response.status_code, status.HTTP_200_OK)

        session_after_logout = self.client.get("/api/auth/session/")
        self.assertEqual(session_after_logout.status_code, status.HTTP_200_OK)
        self.assertFalse(session_after_logout.data["authenticated"])

    def test_login_rejects_invalid_credentials(self):
        response = self.client.post(
            "/api/auth/login/",
            {"username": "editor", "password": "wrong"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "Invalid username or password.")


class SubmissionValidationTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def base_payload(self):
        return {
            "title": "A Valid Title",
            "submission_type": "poetry",
            "artist_name": "Artist Name",
            "pronouns": "they/them",
            "short_bio": "A short but valid bio for the submission.",
            "country_origin": "DK",
            "countries_residence": ["DK"],
            "language": "English",
            "allow_translation": True,
            "text_files": SimpleUploadedFile("poem.pdf", b"test file content", content_type="application/pdf"),
        }

    def test_submission_requires_email(self):
        response = self.client.post("/api/submissions/", self.base_payload(), format="multipart")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_submission_rejects_invalid_email(self):
        payload = self.base_payload()
        payload["email"] = "not-an-email"

        response = self.client.post("/api/submissions/", payload, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)


class SubmissionDownloadsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username="admin",
            password="S3cretPass123",
        )
        self.client.force_authenticate(self.user)

    def test_complete_download_groups_submissions_and_files(self):
        submission = Submission.objects.create(
            title="Archive Piece",
            year="2026",
            description="Detailed description for export output.",
            submission_type=Submission.SubmissionType.POETRY,
            artist_name="Artist One",
            pronouns="they/them",
            short_bio="A short but valid bio for export testing.",
            socials="@artist",
            email="artist@example.com",
            country_origin="DK",
            countries_residence=["DK"],
            language="English",
            allow_translation=True,
            text_file=SimpleUploadedFile("legacy.txt", b"legacy file"),
        )
        SubmissionText.objects.create(
            submission=submission,
            file=SimpleUploadedFile(
                "poem.pdf",
                b"poem content",
                content_type="application/pdf",
            ),
        )
        SubmissionVisual.objects.create(
            submission=submission,
            image=SimpleUploadedFile(
                "image.tiff",
                b"image content",
                content_type="image/tiff",
            ),
        )

        response = self.client.get("/api/downloads/complete/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/zip")

        with ZipFile(BytesIO(response.content)) as archive:
            names = archive.namelist()
            self.assertIn("poetry/", names)
            self.assertIn("poetry/Artist_One/submission.txt", names)
            self.assertIn("poetry/Artist_One/legacy.txt", names)
            self.assertIn("poetry/Artist_One/poem.pdf", names)
            self.assertIn("poetry/Artist_One/image.tiff", names)

            details = archive.read("poetry/Artist_One/submission.txt").decode("utf-8")
            self.assertIn("Title: Archive Piece", details)
            self.assertIn("Email: artist@example.com", details)
            self.assertIn("- legacy.txt", details)
            self.assertIn("- poem.pdf", details)
            self.assertIn("- image.tiff", details)

    def test_excel_download_contains_review_sheet_and_submission_row(self):
        Submission.objects.create(
            title="Spreadsheet Piece",
            year="2026",
            description="Detailed description for spreadsheet output.",
            submission_type=Submission.SubmissionType.LONG_FORM_WRITING,
            artist_name="Artist Two",
            pronouns="she/her",
            short_bio="A short but valid bio for spreadsheet export.",
            socials="@artist-two",
            email="artist.two@example.com",
            country_origin="DK",
            countries_residence=["DE"],
            language="English",
            allow_translation=False,
        )

        response = self.client.get("/api/downloads/excel/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertIn('filename="rage_submissions_volume3.xlsx"', response["Content-Disposition"])

        workbook = load_workbook(filename=BytesIO(response.content))
        self.assertIn("Poetry", workbook.sheetnames)
        self.assertIn("Long form writing", workbook.sheetnames)

        sheet = workbook["Long form writing"]
        header_row = [cell.value for cell in sheet[1]]
        submission_row = [cell.value for cell in sheet[2]]
        expected_headers = [
            "ID",
            "Title",
            "Year",
            "Description",
            "Submission Type",
            "Artist Name",
            "Pronouns",
            "Short Bio",
            "Socials",
            "Email",
            "Country Origin",
            "Countries Residence",
            "Language",
            "Text File",
            "Created At",
        ]

        self.assertEqual(header_row, expected_headers)
        self.assertEqual(submission_row[1], "Spreadsheet Piece")
        self.assertEqual(submission_row[2], "2026")
        self.assertEqual(submission_row[4], "Long form writing")
        self.assertEqual(submission_row[5], "Artist Two")
        self.assertEqual(submission_row[9], "artist.two@example.com")
        self.assertEqual(submission_row[10], "Denmark")
        self.assertEqual(submission_row[11], "Germany")


class SubmissionEmailTests(TestCase):
    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        SUBMISSION_EMAIL_FROM="editor@ragezine.test",
        SUBMISSION_EMAIL_SUBJECT="Submission received",
        SUBMISSION_EMAIL_BODY="Thank you for submitting to Rage Zine.\n\nWe will review your work shortly.",
        SUBMISSION_NOTIFICATION_TO=["internal@ragezine.test"],
    )
    def test_send_submission_emails_sends_applicant_and_internal_messages_with_attachments(self):
        submission = Submission.objects.create(
            title="Mail Piece",
            year="2026",
            description="Detailed description for email output.",
            submission_type=Submission.SubmissionType.POETRY,
            artist_name="Artist Mail",
            pronouns="they/them",
            short_bio="A short but valid bio for email testing.",
            socials="@artistmail",
            email="artist.mail@example.com",
            country_origin="DK",
            countries_residence=["DE"],
            language="English",
            allow_translation=True,
            text_file=SimpleUploadedFile("mail-piece.pdf", b"primary text"),
        )
        SubmissionText.objects.create(
            submission=submission,
            file=SimpleUploadedFile("mail-extra.pdf", b"extra text"),
        )
        SubmissionVisual.objects.create(
            submission=submission,
            image=SimpleUploadedFile("mail-visual.png", b"visual bytes"),
        )

        sent = send_submission_emails(submission)

        self.assertEqual(sent, 2)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[0].from_email, settings.SUBMISSION_EMAIL_FROM)
        self.assertEqual(mail.outbox[0].subject, settings.SUBMISSION_EMAIL_SUBJECT)
        self.assertIn("Thank you for submitting to Rage Zine.", mail.outbox[0].body)
        self.assertIn("Title: Mail Piece", mail.outbox[0].body)
        self.assertEqual(len(mail.outbox[0].attachments), 3)
        self.assertEqual(mail.outbox[0].to, ["artist.mail@example.com"])
        self.assertEqual(mail.outbox[1].to, ["internal@ragezine.test"])
        self.assertEqual(mail.outbox[0].alternatives[0][1], "text/html")
        self.assertIn("Submission Received", mail.outbox[0].alternatives[0][0])
        self.assertIn("Artist Mail", mail.outbox[0].alternatives[0][0])
