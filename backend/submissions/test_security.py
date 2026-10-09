from io import BytesIO
from zipfile import ZipFile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from openpyxl import load_workbook
from rest_framework.test import APIClient

from submissions.models import Submission
from submissions.utils import sanitize_multiline, sanitize_single_line
from submissions.utils.uploads import validate_upload


def valid_payload():
    return {
        "title": "A Valid Title",
        "submission_type": "poetry",
        "artist_name": "Artist Name",
        "pronouns": "they/them",
        "short_bio": "A short but valid bio for this submission.",
        "country_origin": "DK",
        "countries_residence": ["DK"],
        "language": "English",
        "allow_translation": True,
        "email": "artist@example.com",
        "text_files": SimpleUploadedFile("poem.pdf", b"%PDF-1.4\ncontent"),
    }


class PublicInputSecurityTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_text_normalization_keeps_paragraphs_and_removes_controls(self):
        self.assertEqual(sanitize_multiline("First\r\nSecond\tline\u202e"), "First\nSecond line")
        self.assertEqual(sanitize_single_line("First\nSecond\u202e"), "First Second")

    def test_docx_package_is_checked_and_file_position_is_restored(self):
        content = BytesIO()
        with ZipFile(content, "w") as archive:
            archive.writestr("[Content_Types].xml", "<Types/>")
            archive.writestr("word/document.xml", "<document/>")
        upload = SimpleUploadedFile("piece.docx", content.getvalue(), content_type="text/plain")

        validate_upload(upload, "text_files")

        self.assertEqual(upload.tell(), 0)
        self.assertEqual(
            upload.content_type,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    def test_rejects_html_disguised_as_pdf_without_creating_submission(self):
        payload = valid_payload()
        payload["text_files"] = SimpleUploadedFile("poem.pdf", b"<script>alert(1)</script>")

        response = self.client.post("/api/submissions/", payload, format="multipart", REMOTE_ADDR="192.0.2.101")

        self.assertEqual(response.status_code, 400)
        self.assertIn("text_files", response.data)
        self.assertFalse(Submission.objects.exists())

    def test_rejects_unlisted_file_extension(self):
        payload = valid_payload()
        payload["text_files"] = SimpleUploadedFile("program.exe", b"%PDF-1.4\ncontent")

        response = self.client.post("/api/submissions/", payload, format="multipart", REMOTE_ADDR="192.0.2.102")

        self.assertEqual(response.status_code, 400)
        self.assertIn("text_files", response.data)

    def test_rejects_more_than_five_visuals(self):
        payload = valid_payload()
        payload["visuals"] = [
            SimpleUploadedFile(f"image-{index}.tif", b"II*\x00pixels")
            for index in range(6)
        ]

        response = self.client.post("/api/submissions/", payload, format="multipart", REMOTE_ADDR="192.0.2.103")

        self.assertEqual(response.status_code, 400)
        self.assertIn("visuals", response.data)
        self.assertFalse(Submission.objects.exists())

    def test_rejects_unknown_fields_and_oversized_bio(self):
        for extra in ({"unexpected": "value"}, {"short_bio": "x" * 4001}):
            payload = {**valid_payload(), **extra}
            response = self.client.post("/api/submissions/", payload, format="multipart", REMOTE_ADDR="192.0.2.104")
            self.assertEqual(response.status_code, 400)
        self.assertFalse(Submission.objects.exists())


class StaffInputSecurityTests(TestCase):
    def test_login_requires_csrf_token(self):
        user = get_user_model().objects.create_user(
            username="editor", password="S3cretPass123", is_staff=True
        )
        client = APIClient(enforce_csrf_checks=True)

        denied = client.post(
            "/api/auth/login/",
            {"username": user.username, "password": "S3cretPass123"},
            format="json",
        )
        self.assertEqual(denied.status_code, 403)

        csrf_response = client.get("/api/auth/csrf/")
        token = csrf_response.cookies["csrftoken"].value
        accepted = client.post(
            "/api/auth/login/",
            {"username": user.username, "password": "S3cretPass123"},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(accepted.status_code, 200)

    def test_excel_export_keeps_attacker_text_as_text(self):
        Submission.objects.create(
            title='=HYPERLINK("https://example.com", "click")',
            submission_type="poetry",
            artist_name="+cmd|'/C calc'!A0",
            pronouns="they/them",
            short_bio="A short but valid bio for this submission.",
            country_origin="DK",
            countries_residence=["DK"],
            email="artist@example.com",
        )
        client = APIClient()
        client.force_authenticate(get_user_model().objects.create_user(
            username="reviewer", password="S3cretPass123", is_staff=True
        ))

        response = client.get("/api/downloads/excel/")
        sheet = load_workbook(BytesIO(response.content))["Poetry"]

        self.assertEqual(sheet["B2"].data_type, "s")
        self.assertTrue(sheet["B2"].value.startswith("'="))
        self.assertEqual(sheet["F2"].data_type, "s")
        self.assertTrue(sheet["F2"].value.startswith("'+"))

    def test_archive_export_handles_path_like_artist_name(self):
        submission = Submission.objects.create(
            title="A Valid Title",
            submission_type="poetry",
            artist_name="../",
            pronouns="they/them",
            short_bio="A short but valid bio for this submission.",
            country_origin="DK",
            countries_residence=["DK"],
            email="artist@example.com",
        )
        client = APIClient()
        client.force_authenticate(get_user_model().objects.create_user(
            username="reviewer", password="S3cretPass123", is_staff=True
        ))

        response = client.get(f"/api/downloads/submissions/{submission.pk}/")

        self.assertEqual(response.status_code, 200)
        with ZipFile(BytesIO(b"".join(response.streaming_content))) as archive:
            self.assertIn(
                f"poetry/submission-{submission.pk}-{submission.pk}/submission_details.txt",
                archive.namelist(),
            )
