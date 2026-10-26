from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from submissions.models import Submission, Tag


class SubmissionTagTests(TestCase):
    def setUp(self):
        self.submission = Submission.objects.create(
            title="Tagged piece",
            submission_type=Submission.SubmissionType.POETRY,
            artist_name="Artist",
            pronouns="they/them",
            short_bio="A short artist biography.",
            email="artist@example.com",
            country_origin="DK",
            countries_residence=["DK"],
        )
        self.staff = get_user_model().objects.create_user(
            username="tag-editor", password="ExamplePass123!", is_staff=True
        )
        self.staff_client = APIClient()
        self.staff_client.force_authenticate(self.staff)
        self.tag_url = f"/api/submissions/{self.submission.pk}/tags/"

    def test_only_staff_can_list_and_change_tags(self):
        regular_user = get_user_model().objects.create_user(
            username="reader", password="ExamplePass123!"
        )
        for user in (None, regular_user):
            client = APIClient()
            if user:
                client.force_authenticate(user)
            with self.subTest(user=user):
                self.assertEqual(client.get("/api/tags/").status_code, 403)
                self.assertEqual(client.post(self.tag_url, {"name": "reviewed"}).status_code, 403)
                self.assertEqual(client.delete(f"{self.tag_url}1/").status_code, 403)
        self.assertFalse(Tag.objects.exists())

    def test_staff_can_create_and_reuse_normalized_tags(self):
        first = self.staff_client.post(self.tag_url, {"name": "  Visual   Art  "})
        second = self.staff_client.post(self.tag_url, {"name": "VISUAL ART"})
        other_submission = Submission.objects.create(
            title="Another piece",
            submission_type=Submission.SubmissionType.POETRY,
            artist_name="Another artist",
            pronouns="they/them",
            short_bio="Another short biography.",
            email="other@example.com",
            country_origin="DK",
            countries_residence=["DK"],
        )
        third = self.staff_client.post(
            f"/api/submissions/{other_submission.pk}/tags/", {"name": "visual art"}
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(third.status_code, 201)
        self.assertEqual(first.data, second.data)
        self.assertEqual(first.data, third.data)
        self.assertEqual(first.data["name"], "visual art")
        self.assertEqual(Tag.objects.count(), 1)
        self.assertEqual(self.submission.tags.count(), 1)

        self.assertEqual(self.staff_client.get("/api/tags/").data, [first.data])
        details = self.staff_client.get(f"/api/submissions/{self.submission.pk}/")
        self.assertEqual(details.data["tags"], [first.data])
        listing = self.staff_client.get("/api/submissions/")
        self.assertEqual([item["tags"] for item in listing.data], [[first.data], [first.data]])

    def test_public_submission_cannot_assign_tags(self):
        response = APIClient().post(
            "/api/submissions/",
            {
                "title": "A public piece",
                "submission_type": "poetry",
                "artist_name": "Public artist",
                "pronouns": "they/them",
                "short_bio": "A short but valid biography.",
                "email": "public@example.com",
                "country_origin": "DK",
                "countries_residence": ["DK"],
                "text_files": SimpleUploadedFile(
                    "poem.pdf", b"%PDF-1.4\nexample", content_type="application/pdf"
                ),
                "tags": "reviewed",
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Submission.objects.count(), 1)
        self.assertFalse(Tag.objects.exists())

    def test_staff_can_remove_a_tag_without_deleting_the_shared_tag(self):
        tag = self.staff_client.post(self.tag_url, {"name": "reviewed"}).data
        remove_url = f"{self.tag_url}{tag['id']}/"

        self.assertEqual(self.staff_client.delete(remove_url).status_code, 204)
        self.assertEqual(self.staff_client.delete(remove_url).status_code, 404)
        self.assertEqual(self.submission.tags.count(), 0)
        self.assertTrue(Tag.objects.filter(pk=tag["id"]).exists())

    def test_tag_names_and_count_are_limited(self):
        for name in (" ", "<script>", "x" * 51):
            with self.subTest(name=name):
                self.assertEqual(self.staff_client.post(self.tag_url, {"name": name}).status_code, 400)

        for index in range(20):
            self.assertEqual(
                self.staff_client.post(self.tag_url, {"name": f"tag {index}"}).status_code,
                201,
            )
        self.assertEqual(self.staff_client.post(self.tag_url, {"name": "one more"}).status_code, 400)
        self.assertEqual(self.submission.tags.count(), 20)
