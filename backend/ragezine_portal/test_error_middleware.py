from django.http import JsonResponse
from django.test import Client, SimpleTestCase, override_settings
from django.urls import path


def fail(request):
    raise RuntimeError("private internal error detail")


def invalid(request):
    return JsonResponse({"artist_name": ["This field is required."]}, status=400)


urlpatterns = [
    path("api/fail/", fail),
    path("admin/fail/", fail),
    path("api/invalid/", invalid),
]


@override_settings(DEBUG=False, ROOT_URLCONF=__name__, ALLOWED_HOSTS=["testserver"])
class PortalErrorMiddlewareTests(SimpleTestCase):
    def setUp(self):
        self.client = Client(raise_request_exception=False)

    def test_missing_api_route_returns_json(self):
        response = self.client.get("/api/missing/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {
            "detail": "We could not find that page.", "code": "not_found"
        })
        self.assertEqual(response["Cache-Control"], "no-store")

    def test_unhandled_api_error_hides_internal_details(self):
        response = self.client.get("/api/fail/")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {
            "detail": "Please try again later.", "code": "server_error"
        })
        self.assertNotIn(b"private internal error detail", response.content)

    def test_django_pages_get_html_errors(self):
        missing = self.client.get("/admin/missing/")
        failed = self.client.get("/admin/fail/")
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(failed.status_code, 500)
        self.assertContains(missing, "Page not found", status_code=404)
        self.assertContains(failed, "Something went wrong", status_code=500)
        self.assertContains(failed, 'href="/admin/"', status_code=500)
        self.assertNotIn(b"private internal error detail", failed.content)

    def test_validation_errors_keep_field_details(self):
        response = self.client.get("/api/invalid/")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"artist_name": ["This field is required."]})
