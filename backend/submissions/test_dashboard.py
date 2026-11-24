from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from submissions.models import Artist, Submission, Tag, Work


class DashboardListTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username="dashboard-reviewer", password="test-password", is_staff=True,
        )

    def add_submission(self, name, title, work_type="poetry", description="A complete description"):
        artist = Artist.objects.create(
            artist_name=name, pronouns="they/them", email=f"{name.replace(' ', '')}@example.com",
            country_origin="DK", countries_residence=["DK"], short_bio="A short artist bio.",
        )
        submission = Submission.objects.create(
            artist=artist, artist_name=name, pronouns="they/them",
            email=artist.email, country_origin="DK", countries_residence=["DK"],
            short_bio=artist.short_bio, title=title, description=description,
            submission_type=work_type,
        )
        Work.objects.create(
            submission=submission, position=1, title=title,
            description=description, submission_type=work_type,
        )
        return submission

    def test_staff_receives_one_page_and_counts(self):
        for index in range(23):
            self.add_submission(f"Artist {index}", f"Piece {index}")
        self.assertEqual(self.client.get("/api/submissions/dashboard/").status_code, 403)
        self.client.force_authenticate(self.user)
        first = self.client.get("/api/submissions/dashboard/")
        second = self.client.get("/api/submissions/dashboard/?page=2")
        self.assertEqual(first.status_code, 200)
        self.assertEqual((first.data["count"], first.data["total"], len(first.data["results"])), (23, 23, 20))
        self.assertEqual(len(second.data["results"]), 3)
        self.assertFalse({row["id"] for row in first.data["results"]} & {row["id"] for row in second.data["results"]})
        self.assertEqual(first.data["summary"][0]["count"], 23)

    def test_search_type_tag_and_sort_keep_matching_works(self):
        target = self.add_submission("A Artist", "Golden River", "poetry")
        self.add_submission("Z Artist", "Blue Garden", "visual_art")
        tag = Tag.objects.create(name="shortlist")
        target.tags.add(tag)
        self.client.force_authenticate(self.user)

        fuzzy = self.client.get("/api/submissions/dashboard/?query=goldn")
        self.assertEqual([row["id"] for row in fuzzy.data["results"]], [target.id])
        self.assertEqual(fuzzy.data["summary"][0]["count"], 1)
        by_tag = self.client.get(f"/api/submissions/dashboard/?tag={tag.id}&type=visual_art")
        self.assertEqual((by_tag.data["base_count"], by_tag.data["count"]), (1, 0))
        by_name = self.client.get("/api/submissions/dashboard/?sort=artist_desc")
        self.assertEqual(by_name.data["results"][0]["artist"]["artist_name"], "Z Artist")
        self.assertEqual(by_name.data["tags"][0]["name"], "shortlist")

    def test_invalid_legacy_type_is_uncategorized(self):
        legacy = self.add_submission("Legacy Artist", "Old Piece", "old_type")
        self.client.force_authenticate(self.user)
        response = self.client.get("/api/submissions/dashboard/?type=uncategorized")
        self.assertEqual([row["id"] for row in response.data["results"]], [legacy.id])
        self.assertEqual(response.data["summary"][0], {
            "type": "uncategorized", "label": "uncategorized", "count": 1,
        })

    def test_short_search_does_not_match_unrelated_title(self):
        self.add_submission("First Artist", "Golden River")
        self.client.force_authenticate(self.user)
        response = self.client.get("/api/submissions/dashboard/?query=go")
        self.assertEqual(response.data["count"], 1)
        response = self.client.get("/api/submissions/dashboard/?query=gi")
        self.assertEqual(response.data["count"], 0)
