from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework.throttling import SimpleRateThrottle


TEST_RATES = {
    "submission_create": "2/hour",
    "login_ip": "3/minute",
    "login_username": "2/minute",
    "staff_export": "2/hour",
}


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "rate-limit-endpoint-tests",
        }
    },
)
class RateLimitEndpointTests(TestCase):
    def setUp(self):
        rate_patch = patch.object(SimpleRateThrottle, "THROTTLE_RATES", TEST_RATES)
        rate_patch.start()
        self.addCleanup(rate_patch.stop)
        cache.clear()
        self.client = APIClient()

    def tearDown(self):
        cache.clear()
        super().tearDown()

    def test_public_submission_limit_is_per_ip_and_returns_retry_after(self):
        url = "/api/submissions/"
        first_ip = {"REMOTE_ADDR": "192.0.2.10"}
        second_ip = {"REMOTE_ADDR": "192.0.2.11"}

        self.assertEqual(self.client.post(url, {}, format="json", **first_ip).status_code, 400)
        self.assertEqual(self.client.post(url, {}, format="json", **first_ip).status_code, 400)
        blocked = self.client.post(url, {}, format="json", **first_ip)
        self.assertEqual(blocked.status_code, 429)
        self.assertIn("Retry-After", blocked)
        self.assertEqual(self.client.post(url, {}, format="json", **second_ip).status_code, 400)

    def test_login_limits_by_ip_and_username_across_ips(self):
        url = "/api/auth/login/"
        payload = {"username": "Editor", "password": "wrong"}
        first_ip = {"REMOTE_ADDR": "192.0.2.20"}
        second_ip = {"REMOTE_ADDR": "192.0.2.21"}

        self.assertEqual(self.client.post(url, payload, format="json", **first_ip).status_code, 400)
        self.assertEqual(self.client.post(url, payload, format="json", **second_ip).status_code, 400)
        blocked_name = self.client.post(
            url, {"username": "editor", "password": "wrong"}, format="json", **second_ip
        )
        self.assertEqual(blocked_name.status_code, 429)
        self.assertIn("Retry-After", blocked_name)

        other_name = {"username": "someone-else", "password": "wrong"}
        self.assertEqual(self.client.post(url, other_name, format="json", **first_ip).status_code, 400)
        self.assertEqual(self.client.post(url, other_name, format="json", **first_ip).status_code, 400)
        blocked_ip = self.client.post(url, other_name, format="json", **first_ip)
        self.assertEqual(blocked_ip.status_code, 429)

    def test_staff_download_limit_is_shared_across_exports_and_per_user(self):
        user_model = get_user_model()
        first_staff = user_model.objects.create_user(
            username="editor-one", password="test-password", is_staff=True
        )
        second_staff = user_model.objects.create_user(
            username="editor-two", password="test-password", is_staff=True
        )
        self.client.force_authenticate(user=first_staff)

        with patch("submissions.api.downloads._build_complete_download_zip", return_value=b"zip"):
            with patch(
                "submissions.api.downloads._build_excel_workbook",
                return_value=(b"excel", "submissions.xlsx"),
            ):
                self.assertEqual(self.client.get("/api/downloads/complete/").status_code, 200)
                self.assertEqual(self.client.get("/api/downloads/excel/").status_code, 200)
                blocked = self.client.get("/api/downloads/complete/")
                self.assertEqual(blocked.status_code, 429)
                self.assertIn("Retry-After", blocked)

                self.client.force_authenticate(user=second_staff)
                self.assertEqual(self.client.get("/api/downloads/complete/").status_code, 200)
