from io import BytesIO
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from zipfile import ZipFile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient
from storages.backends.s3 import S3Storage

from submissions.models import Submission, SubmissionDocument


class SubmissionDetailsTests(TestCase):
    def setUp(self):
        temporary_storage = TemporaryDirectory()
        self.addCleanup(temporary_storage.cleanup)
        storage_override = override_settings(STORAGES={
            "default": {
                "BACKEND": "django.core.files.storage.FileSystemStorage",
                "OPTIONS": {"location": temporary_storage.name},
            },
            "staticfiles": {
                "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
            },
        })
        storage_override.enable()
        self.addCleanup(storage_override.disable)

        self.submission = Submission.objects.create(
            title="A Test Submission",
            submission_type="poetry",
            artist_name="Artist Name",
            pronouns="they/them",
            short_bio="A short biography for the artist.",
            email="artist@example.com",
            country_origin="DK",
            countries_residence=["DK"],
        )
        self.staff = get_user_model().objects.create_user(
            username="reviewer", password="S3cretPass123", is_staff=True
        )
        self.reader = get_user_model().objects.create_user(
            username="reader", password="S3cretPass123", is_staff=False
        )
        self.client = APIClient()
        self.client.force_authenticate(self.staff)

    def add_document(self, filename, content, content_type):
        return SubmissionDocument.create_from_upload(
            submission=self.submission,
            uploaded_file=SimpleUploadedFile(filename, content, content_type=content_type),
            document_type=SubmissionDocument.DocumentType.TEXT,
        )

    def test_staff_can_read_details_and_post_comments(self):
        document = self.add_document("poem.pdf", b"%PDF-1.4\npreview", "application/pdf")
        detail_url = f"/api/submissions/{self.submission.pk}/"
        comments_url = f"{detail_url}comments/"

        detail = self.client.get(detail_url)
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data["title"], self.submission.title)
        self.assertEqual(detail.data["country_origin_name"], "Denmark")
        self.assertEqual(detail.data["documents"][0]["preview_kind"], "pdf")
        self.assertEqual(
            detail.data["documents"][0]["preview_url"],
            f"/api/previews/documents/{document.pk}/",
        )
        self.assertEqual(self.client.get(comments_url).data, [])

        created = self.client.post(
            comments_url, {"body": "  First note.\n  Second line.  "}, format="json"
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data["body"], "First note.\nSecond line.")
        self.assertEqual(created.data["author_name"], "reviewer")
        listed = self.client.get(comments_url)
        self.assertEqual(len(listed.data), 1)
        self.assertEqual(listed.data[0]["id"], created.data["id"])

    def test_comments_and_previews_are_staff_only(self):
        document = self.add_document("poem.pdf", b"%PDF-1.4\npreview", "application/pdf")
        comments_url = f"/api/submissions/{self.submission.pk}/comments/"
        preview_url = f"/api/previews/documents/{document.pk}/"

        for user in (None, self.reader):
            visitor = APIClient()
            if user:
                visitor.force_authenticate(user)
            with self.subTest(user=user):
                self.assertEqual(visitor.get(comments_url).status_code, 403)
                self.assertEqual(
                    visitor.post(comments_url, {"body": "Private note"}, format="json").status_code,
                    403,
                )
                self.assertEqual(visitor.get(preview_url).status_code, 403)

    def test_comment_requires_text_within_limit(self):
        comments_url = f"/api/submissions/{self.submission.pk}/comments/"
        self.assertEqual(
            self.client.post(comments_url, {"body": "  "}, format="json").status_code,
            400,
        )
        self.assertEqual(
            self.client.post(comments_url, {"body": "x" * 4001}, format="json").status_code,
            400,
        )
        self.assertEqual(self.submission.staff_comments.count(), 0)

    def test_pdf_preview_streams_requested_byte_range(self):
        content = b"%PDF-1.4\npreview"
        document = self.add_document("poem.pdf", content, "application/pdf")
        url = f"/api/previews/documents/{document.pk}/"

        response = self.client.get(url, HTTP_RANGE="bytes=2-6")
        self.assertEqual(response.status_code, 206)
        self.assertEqual(response["Content-Range"], f"bytes 2-6/{len(content)}")
        self.assertEqual(response["Content-Length"], "5")
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertEqual(response["X-Frame-Options"], "SAMEORIGIN")
        self.assertEqual(b"".join(response.streaming_content), content[2:7])
        response.close()

        suffix = self.client.get(url, HTTP_RANGE="bytes=-4")
        self.assertEqual(suffix.status_code, 206)
        self.assertEqual(b"".join(suffix.streaming_content), content[-4:])
        suffix.close()

        invalid = self.client.get(url, HTTP_RANGE="bytes=500-")
        self.assertEqual(invalid.status_code, 416)
        self.assertEqual(invalid["Content-Range"], f"bytes */{len(content)}")

    def test_video_preview_streams_a_requested_range(self):
        content = b"\x00\x00\x00\x18ftypmp42video-bytes"
        document = self.add_document("clip.mp4", content, "video/mp4")
        response = self.client.get(
            f"/api/previews/documents/{document.pk}/", HTTP_RANGE="bytes=4-11"
        )
        self.assertEqual(response.status_code, 206)
        self.assertEqual(response["Content-Type"], "video/mp4")
        self.assertEqual(response["Accept-Ranges"], "bytes")
        self.assertEqual(b"".join(response.streaming_content), content[4:12])
        response.close()

    def test_local_video_access_uses_private_preview(self):
        document = self.add_document("clip.mp4", b"video-bytes", "video/mp4")
        url = f"/api/previews/documents/{document.pk}/video-access/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["url"], f"/api/previews/documents/{document.pk}/")
        self.assertIsNone(response.data["expires_in"])
        self.assertEqual(response["Cache-Control"], "private, no-store")

        for user in (None, self.reader):
            visitor = APIClient()
            if user:
                visitor.force_authenticate(user)
            with self.subTest(user=user):
                self.assertEqual(visitor.get(url).status_code, 403)

        other = self.add_document("poem.pdf", b"%PDF-1.4", "application/pdf")
        self.assertEqual(
            self.client.get(f"/api/previews/documents/{other.pk}/video-access/").status_code,
            415,
        )

    def test_s3_video_access_returns_a_signed_get_url(self):
        document = self.add_document("clip.mp4", b"video-bytes", "video/mp4")
        storage = S3Storage(
            bucket_name="review-example-bucket",
            region_name="eu-central-1",
            endpoint_url="https://s3.eu-central-1.amazonaws.com",
            addressing_style="virtual",
            access_key="test-access-key",
            secret_key="test-secret-key",
            querystring_auth=True,
        )
        field = SubmissionDocument._meta.get_field("file")
        with patch.object(field, "storage", storage):
            response = self.client.get(
                f"/api/previews/documents/{document.pk}/video-access/"
            )
            old_preview = self.client.get(
                f"/api/previews/documents/{document.pk}/"
            )
            redirected = self.client.get(
                f"/api/previews/documents/{document.pk}/video-access/?redirect=1"
            )

        self.assertEqual(response.status_code, 200)
        signed_url = urlsplit(response.data["url"])
        self.assertEqual(signed_url.scheme, "https")
        self.assertEqual(
            signed_url.netloc,
            "review-example-bucket.s3.eu-central-1.amazonaws.com",
        )
        self.assertIn(document.file.name, signed_url.path)
        self.assertIn("X-Amz-Signature", parse_qs(signed_url.query))
        self.assertEqual(response.data["expires_in"], 3600)
        self.assertEqual(old_preview.status_code, 302)
        self.assertEqual(
            old_preview["Location"],
            f"/api/previews/documents/{document.pk}/video-access/?redirect=1",
        )
        self.assertEqual(redirected.status_code, 302)
        self.assertIn("X-Amz-Signature", parse_qs(urlsplit(redirected["Location"]).query))
        self.assertEqual(redirected["Cache-Control"], "private, no-store")

    def test_s3_video_access_rejects_unsigned_storage(self):
        document = self.add_document("clip.mp4", b"video-bytes", "video/mp4")
        storage = S3Storage(
            bucket_name="review-example-bucket",
            region_name="eu-central-1",
            access_key="test-access-key",
            secret_key="test-secret-key",
            querystring_auth=False,
        )
        field = SubmissionDocument._meta.get_field("file")
        with patch.object(field, "storage", storage):
            response = self.client.get(
                f"/api/previews/documents/{document.pk}/video-access/"
            )
        self.assertEqual(response.status_code, 503)

    def test_docx_and_tiff_have_safe_previews(self):
        docx = BytesIO()
        with ZipFile(docx, "w") as archive:
            archive.writestr(
                "word/document.xml",
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                "<w:body><w:p><w:r><w:t>First paragraph.</w:t></w:r></w:p>"
                "<w:p><w:r><w:t>Second paragraph.</w:t></w:r></w:p></w:body></w:document>",
            )
        word_file = self.add_document(
            "draft.docx", docx.getvalue(),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        word_preview = self.client.get(f"/api/previews/documents/{word_file.pk}/")
        self.assertEqual(word_preview.status_code, 200)
        self.assertTrue(word_preview["Content-Type"].startswith("text/plain"))
        self.assertIn(b"First paragraph.\n\nSecond paragraph.", word_preview.content)

        tiff = BytesIO()
        Image.new("RGB", (12, 8), "red").save(tiff, format="TIFF")
        image_file = self.add_document("art.tiff", tiff.getvalue(), "image/tiff")
        image_preview = self.client.get(f"/api/previews/documents/{image_file.pk}/")
        self.assertEqual(image_preview.status_code, 200)
        self.assertEqual(image_preview["Content-Type"], "image/png")
        self.assertTrue(image_preview.content.startswith(b"\x89PNG\r\n\x1a\n"))

    def test_unsupported_file_does_not_render_inline(self):
        document = self.add_document("page.html", b"<script>alert(1)</script>", "text/html")
        detail = self.client.get(f"/api/submissions/{self.submission.pk}/")
        self.assertIsNone(detail.data["documents"][0]["preview_url"])
        response = self.client.get(f"/api/previews/documents/{document.pk}/")
        self.assertEqual(response.status_code, 415)

    def test_malformed_word_file_returns_preview_error(self):
        document = self.add_document("broken.docx", b"not a Word document", "application/octet-stream")
        response = self.client.get(f"/api/previews/documents/{document.pk}/")
        self.assertEqual(response.status_code, 422)
