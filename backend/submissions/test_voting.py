from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.test import TestCase
from rest_framework.test import APIClient

from submissions.models import Submission, SubmissionComment, SubmissionVote


class SubmissionVotingTests(TestCase):
    def setUp(self):
        self.submission = Submission.objects.create(
            title="Voting test",
            submission_type="poetry",
            artist_name="Artist",
            pronouns="they/them",
            short_bio="A biography for the artist.",
            email="artist@example.com",
            country_origin="DK",
            countries_residence=["DK"],
        )
        user_model = get_user_model()
        self.alex = user_model.objects.create_user(
            username="alex", password="S3cretPass123", is_staff=True
        )
        self.blair = user_model.objects.create_user(
            username="blair", password="S3cretPass123", is_staff=True
        )
        self.reader = user_model.objects.create_user(
            username="reader", password="S3cretPass123", is_staff=False
        )
        self.client = APIClient()
        self.client.force_authenticate(self.alex)
        self.votes_url = f"/api/submissions/{self.submission.pk}/votes/"

    def test_each_staff_account_has_one_changeable_vote(self):
        empty = self.client.get(self.votes_url)
        self.assertEqual(empty.status_code, 200)
        self.assertEqual(
            empty.data["counts"],
            {"yes": 0, "no": 0, "see_comment": 0, "total": 0},
        )
        self.assertIsNone(empty.data["my_vote"])

        first = self.client.post(self.votes_url, {"choice": "yes"}, format="json")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.data["counts"]["yes"], 1)
        self.assertEqual(first.data["my_vote"]["voter_name"], "alex")

        old_time = timezone.now() - timedelta(days=1)
        SubmissionVote.objects.filter(voter=self.alex).update(updated_at=old_time)
        unchanged = self.client.post(self.votes_url, {"choice": "yes"}, format="json")
        self.assertEqual(unchanged.status_code, 200)
        self.assertEqual(SubmissionVote.objects.get().updated_at, old_time)

        changed = self.client.post(self.votes_url, {"choice": "no"}, format="json")
        self.assertEqual(changed.status_code, 200)
        self.assertEqual(changed.data["counts"]["yes"], 0)
        self.assertEqual(changed.data["counts"]["no"], 1)
        self.assertGreater(SubmissionVote.objects.get().updated_at, old_time)
        self.assertEqual(SubmissionVote.objects.count(), 1)

        self.client.force_authenticate(self.blair)
        second = self.client.post(self.votes_url, {"choice": "yes"}, format="json")
        self.assertEqual(second.status_code, 201)
        self.assertEqual(second.data["counts"]["total"], 2)
        self.assertEqual(
            {(vote["voter_name"], vote["choice"]) for vote in second.data["votes"]},
            {("alex", "no"), ("blair", "yes")},
        )

        overview = self.client.get("/api/submissions/")
        self.assertEqual(overview.status_code, 200)
        self.assertEqual(
            overview.data[0]["vote_counts"],
            {"yes": 1, "no": 1, "see_comment": 0, "total": 2},
        )
        detail = self.client.get(f"/api/submissions/{self.submission.pk}/")
        self.assertEqual(detail.data["vote_counts"], overview.data[0]["vote_counts"])

    def test_see_comment_is_only_a_vote_choice(self):
        first = self.client.post(
            self.votes_url, {"choice": "see_comment"}, format="json"
        )
        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.data["counts"]["see_comment"], 1)
        self.assertEqual(first.data["my_vote"]["choice"], "see_comment")
        self.assertNotIn("comment", first.data["my_vote"])
        self.assertFalse(SubmissionComment.objects.exists())

        invalid = self.client.post(
            self.votes_url,
            {"choice": "see_comment", "comment": "No vote comments"},
            format="json",
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(SubmissionVote.objects.get().choice, "see_comment")

        changed = self.client.post(self.votes_url, {"choice": "no"}, format="json")
        self.assertEqual(changed.status_code, 200)
        self.assertEqual(changed.data["counts"]["see_comment"], 0)
        self.assertEqual(changed.data["counts"]["no"], 1)
        self.assertEqual(SubmissionVote.objects.count(), 1)
        self.assertFalse(SubmissionComment.objects.exists())

    def test_votes_are_staff_only(self):
        for user in (None, self.reader):
            visitor = APIClient()
            if user:
                visitor.force_authenticate(user)
            with self.subTest(user=user):
                self.assertEqual(visitor.get(self.votes_url).status_code, 403)
                self.assertEqual(
                    visitor.post(
                        self.votes_url, {"choice": "yes"}, format="json"
                    ).status_code,
                    403,
                )
        self.assertFalse(SubmissionVote.objects.exists())

    def test_invalid_choice_does_not_create_a_vote(self):
        response = self.client.post(
            self.votes_url, {"choice": "maybe"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(SubmissionVote.objects.exists())
