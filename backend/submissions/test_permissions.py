from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.http import Http404
from django.test import SimpleTestCase, override_settings
from django.urls import Resolver404, resolve
from rest_framework.response import Response
from rest_framework.test import APIClient, APIRequestFactory

from submissions.admin import ProtectedAdminFileWidget
from submissions.api.submission_views import SubmissionViewSet
from submissions.models import SubmissionDocument
from submissions.serializers import SubmissionDocumentSerializer


class SubmissionPermissionTests(SimpleTestCase):
    protected_actions = (
        ("get", "/api/submissions/", "list"),
        ("get", "/api/submissions/1/", "retrieve"),
        ("put", "/api/submissions/1/", "update"),
        ("patch", "/api/submissions/1/", "partial_update"),
        ("delete", "/api/submissions/1/", "destroy"),
    )

    def request_action(self, method, path, action, user=None):
        client = APIClient()
        if user is not None:
            client.force_authenticate(user=user)

        expected_status = 201 if action == "create" else 200
        with patch.object(
            SubmissionViewSet,
            action,
            return_value=Response({"ok": True}, status=expected_status),
        ) as handler:
            response = getattr(client, method)(
                path, {}, format="json", REMOTE_ADDR="192.0.2.200"
            )
        return response, handler

    def test_anonymous_visitors_can_create_submissions(self):
        response, handler = self.request_action(
            "post", "/api/submissions/", "create"
        )

        self.assertEqual(response.status_code, 201)
        handler.assert_called_once()

    def test_anonymous_and_nonstaff_users_cannot_review_or_change_submissions(self):
        regular_user = get_user_model()(username="reader", is_staff=False)
        for user in (None, regular_user):
            for method, path, action in self.protected_actions:
                with self.subTest(user=user, action=action):
                    response, handler = self.request_action(method, path, action, user)
                    self.assertEqual(response.status_code, 403)
                    handler.assert_not_called()

    def test_staff_users_can_review_and_change_submissions(self):
        staff_user = get_user_model()(username="editor", is_staff=True)
        for method, path, action in self.protected_actions:
            with self.subTest(action=action):
                response, handler = self.request_action(method, path, action, staff_user)
                self.assertEqual(response.status_code, 200)
                handler.assert_called_once()


class StaffLoginPermissionTests(SimpleTestCase):
    def test_staff_credentials_create_a_session(self):
        staff_user = get_user_model()(username="editor", is_staff=True)
        with patch("submissions.api.auth.authenticate", return_value=staff_user):
            with patch("submissions.api.auth.login") as login:
                response = APIClient().post(
                    "/api/auth/login/",
                    {"username": "editor", "password": "valid-password"},
                    format="json",
                )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["user"]["is_staff"])
        login.assert_called_once()

    def test_nonstaff_credentials_do_not_create_a_session(self):
        regular_user = get_user_model()(username="reader", is_staff=False)
        with patch("submissions.api.auth.authenticate", return_value=regular_user):
            with patch("submissions.api.auth.login") as login:
                response = APIClient().post(
                    "/api/auth/login/",
                    {"username": "reader", "password": "valid-password"},
                    format="json",
                )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["message"], "Invalid username or password.")
        login.assert_not_called()


class DownloadPermissionTests(SimpleTestCase):
    urls = (
        "/api/downloads/complete/",
        "/api/downloads/excel/",
        "/api/downloads/submissions/1/",
    )

    def test_anonymous_and_nonstaff_users_cannot_download(self):
        regular_user = get_user_model()(username="reader", is_staff=False)
        for user in (None, regular_user):
            client = APIClient()
            if user is not None:
                client.force_authenticate(user=user)
            for url in self.urls:
                with self.subTest(user=user, url=url):
                    self.assertEqual(client.get(url).status_code, 403)

    def test_staff_users_can_reach_download_endpoints(self):
        client = APIClient()
        client.force_authenticate(
            user=get_user_model()(username="editor", is_staff=True)
        )
        with patch(
            "submissions.api.downloads._build_complete_download_zip",
            side_effect=lambda: BytesIO(b"zip"),
        ), patch(
            "submissions.api.downloads._build_excel_workbook",
            return_value=(b"workbook", "review.xlsx"),
        ), patch(
            "submissions.api.downloads.get_object_or_404",
            return_value=object(),
        ), patch(
            "submissions.api.downloads._build_submission_download_zip",
            side_effect=lambda submission: (BytesIO(b"zip"), "submission.zip"),
        ):
            for url in self.urls:
                with self.subTest(url=url):
                    self.assertEqual(client.get(url).status_code, 200)


class ProtectedDocumentTests(SimpleTestCase):
    url = "/api/downloads/documents/7/"

    def test_only_staff_can_download_documents(self):
        regular_user = get_user_model()(username="reader", is_staff=False)
        for user in (None, regular_user):
            client = APIClient()
            if user is not None:
                client.force_authenticate(user=user)
            with self.subTest(user=user):
                with patch("submissions.api.downloads.get_object_or_404") as lookup:
                    self.assertEqual(client.get(self.url).status_code, 403)
                    lookup.assert_not_called()

    def test_staff_downloads_attachment_from_storage(self):
        stored_file = BytesIO(b"private document bytes")
        stored_file.name = "submissions/texts/poem.pdf"
        stored_file.storage = SimpleNamespace(exists=lambda name: True)
        stored_file.open = lambda mode: stored_file
        document = SimpleNamespace(file=stored_file, original_filename="poem.pdf")
        client = APIClient()
        client.force_authenticate(user=get_user_model()(username="editor", is_staff=True))

        with patch("submissions.api.downloads.get_object_or_404", return_value=document):
            response = client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/octet-stream")
        self.assertIn('attachment; filename="poem.pdf"', response["Content-Disposition"])
        self.assertEqual(b"".join(response.streaming_content), b"private document bytes")
        response.close()

    def test_missing_document_returns_404(self):
        client = APIClient()
        client.force_authenticate(user=get_user_model()(username="editor", is_staff=True))
        with patch("submissions.api.downloads.get_object_or_404", side_effect=Http404):
            self.assertEqual(client.get(self.url).status_code, 404)

    def test_serializer_and_admin_use_protected_link(self):
        document = SubmissionDocument(id=7, original_filename="poem.pdf")
        document.file.name = "submissions/texts/poem.pdf"
        request = APIRequestFactory().get("/")
        data = SubmissionDocumentSerializer(document, context={"request": request}).data

        self.assertNotIn("file", data)
        self.assertEqual(data["download_url"], f"http://testserver{self.url}")
        widget = ProtectedAdminFileWidget()
        context = widget.get_context("file", document.file, {})
        self.assertEqual(context["widget"]["value"].url, self.url)
        self.assertEqual(str(context["widget"]["value"]), "poem.pdf")

        unsaved_document = SubmissionDocument(file="submissions/texts/draft.pdf")
        self.assertFalse(widget.get_context("file", unsaved_document.file, {})["widget"]["is_initial"])

    @override_settings(DEBUG=True)
    def test_public_media_route_is_not_registered(self):
        with self.assertRaises(Resolver404):
            resolve("/media/submissions/texts/poem.pdf")
