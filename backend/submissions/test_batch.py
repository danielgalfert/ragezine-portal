import json
from io import BytesIO
from unittest.mock import patch
from zipfile import ZipFile
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.core import mail
from rest_framework.test import APIClient
from openpyxl import load_workbook

from submissions.models import Artist, Submission, SubmissionComment, SubmissionVote, Tag, Work


class SubmissionBatchTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        storage_override = override_settings(STORAGES={
            **settings.STORAGES,
            "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
        })
        storage_override.enable()
        self.addCleanup(storage_override.disable)
        self.artist = {
            "artist_name": "Artist Name",
            "pronouns": "they/them",
            "email": "artist@example.com",
            "country_origin": ["DK"],
            "countries_residence": ["DE"],
            "short_bio": "A short bio for this artist.",
            "socials": "@artist",
            "message_to_editors": "Please consider both pieces.  ",
            "submitted_before": False,
            "featured_before": True,
        }
        self.pieces = [
            {
                "submission_type": "poetry",
                "title": "First Piece",
                "description": "A description of the first piece.",
                "language": "English",
                "published_elsewhere": False,
                "anything_else": "A note about the piece.  ",
            },
            {
                "submission_type": "other",
                "title": "Second Piece",
                "description": "A description of the second piece.",
                "language": "English",
                "published_elsewhere": True,
                "published_where": "Example journal",
                "other_links": ["https://example.com/work"],
            },
        ]

    def post_batch(self, pieces=None, artist=None, **files):
        return self.client.post(
            "/api/submissions/batch/",
            {
                "artist": json.dumps(self.artist if artist is None else artist),
                "submissions": json.dumps(self.pieces if pieces is None else pieces),
                **files,
            },
            format="multipart",
            REMOTE_ADDR="198.51.100.230",
        )

    def test_two_pieces_share_artist_and_batch_id(self):
        upload = SimpleUploadedFile("poem.pdf", b"%PDF-1.4\ncontent", content_type="application/pdf")
        with patch("submissions.api.submission_views.send_batch_receipt") as receipt:
            response = self.post_batch(submission_0_text_files=upload)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Submission.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 1)
        submission = Submission.objects.get()
        first, second = list(submission.works.all())
        self.assertEqual((first.position, second.position), (1, 2))
        self.assertEqual(submission.artist.artist_name, "Artist Name")
        self.assertEqual(submission.artist.message_to_editors, "Please consider both pieces.")
        self.assertEqual(first.anything_else, "A note about the piece.")
        self.assertEqual(first.documents.count(), 1)
        self.assertEqual(second.links.count(), 1)
        self.assertEqual(second.submission_type, "other")
        self.assertEqual(response.data["batch_id"], str(submission.batch_id))
        self.assertEqual(len(response.data["submission"]["works"]), 2)
        self.assertTrue(all(work.created_at for work in (first, second)))
        receipt.assert_called_once()

    def test_work_download_contains_only_selected_work(self):
        first_file = SimpleUploadedFile("first.pdf", b"%PDF-1.4\nfirst", content_type="application/pdf")
        second_file = SimpleUploadedFile("second.pdf", b"%PDF-1.4\nsecond", content_type="application/pdf")
        with patch("submissions.api.submission_views.send_batch_receipt"):
            response = self.post_batch(submission_0_text_files=first_file, submission_1_text_files=second_file)
        self.assertEqual(response.status_code, 201)
        first, second = Submission.objects.get().works.all()
        url = f"/api/downloads/works/{first.pk}/"
        self.assertIn(self.client.get(url).status_code, (401, 403))

        reviewer = get_user_model().objects.create_user(username="download-reviewer", password="test-password", is_staff=True)
        self.client.force_authenticate(reviewer)
        download = self.client.get(url)
        self.assertEqual(download.status_code, 200)
        self.assertEqual(download["Content-Type"], "application/zip")
        with ZipFile(BytesIO(b"".join(download.streaming_content))) as archive:
            names = archive.namelist()
            self.assertTrue(any(name.endswith("/piece-1/first.pdf") for name in names))
            self.assertFalse(any("second.pdf" in name for name in names))
            details = archive.read(next(name for name in names if name.endswith("submission_details.txt"))).decode("utf-8")
            self.assertIn(first.title, details)
            self.assertNotIn(second.title, details)
        self.assertEqual(self.client.get(f"/api/downloads/works/{second.pk + 10000}/").status_code, 404)

    def test_complete_download_separates_pieces_and_includes_excel_index(self):
        first_file = SimpleUploadedFile("first.pdf", b"%PDF-1.4\nfirst", content_type="application/pdf")
        second_file = SimpleUploadedFile("second.pdf", b"%PDF-1.4\nsecond", content_type="application/pdf")
        with patch("submissions.api.submission_views.send_batch_receipt"):
            response = self.post_batch(submission_0_text_files=first_file, submission_1_text_files=second_file)
        self.assertEqual(response.status_code, 201)
        submission = Submission.objects.get()
        reviewer = get_user_model().objects.create_user(username="complete-reviewer", password="test-password", is_staff=True)
        self.client.force_authenticate(reviewer)

        download = self.client.get("/api/downloads/complete/")
        self.assertEqual(download.status_code, 200)
        with ZipFile(BytesIO(b"".join(download.streaming_content))) as archive:
            root = f"submissions/Artist_Name-{submission.pk}"
            self.assertEqual(archive.read(f"{root}/piece-1/first.pdf"), b"%PDF-1.4\nfirst")
            self.assertEqual(archive.read(f"{root}/piece-2/second.pdf"), b"%PDF-1.4\nsecond")
            first_details = archive.read(f"{root}/piece-1/piece_details.txt").decode("utf-8")
            second_details = archive.read(f"{root}/piece-2/piece_details.txt").decode("utf-8")
            self.assertIn("First Piece", first_details)
            self.assertNotIn("Second Piece", first_details)
            self.assertIn("Second Piece", second_details)
            self.assertNotIn("First Piece", second_details)
            workbook_name = next(name for name in archive.namelist() if name.endswith(".xlsx"))
            workbook = load_workbook(BytesIO(archive.read(workbook_name)))
            self.assertEqual(workbook["Submissions"]["A2"].value, submission.pk)
            self.assertEqual(workbook["Poetry"]["E2"].value, "First Piece")
            self.assertEqual(workbook["Other"]["E2"].value, "Second Piece")

    def test_later_batch_with_matching_artist_and_email_stays_separate(self):
        upload = SimpleUploadedFile("poem.pdf", b"%PDF-1.4\ncontent", content_type="application/pdf")
        with patch("submissions.api.submission_views.send_batch_receipt"):
            first_response = self.post_batch(submission_0_text_files=upload)
        self.assertEqual(first_response.status_code, 201)
        submission = Submission.objects.get()
        original_batch_id = submission.batch_id
        reviewer = get_user_model().objects.create_user(username="reviewer", password="test-password", is_staff=True)
        SubmissionVote.objects.create(submission=submission, voter=reviewer, choice="yes")
        SubmissionComment.objects.create(submission=submission, author=reviewer, author_name="reviewer", body="Review note")
        submission.tags.add(Tag.objects.create(name="shortlist"))

        later_artist = {
            **self.artist,
            "artist_name": "  artist name  ",
            "email": "ARTIST@EXAMPLE.COM",
            "pronouns": "she/her",
            "short_bio": "A newer bio for the same artist.",
            "socials": "@newartist",
            "country_origin": ["SE"],
            "countries_residence": ["NO"],
            "message_to_editors": "A note for the later work.",
            "submitted_before": True,
        }
        later_piece = {**self.pieces[0], "title": "Later Piece", "named_links": [
            {"name": "Draft", "url": "https://example.com/later"},
        ]}
        with patch("submissions.api.submission_views.send_batch_receipt") as receipt:
            response = self.post_batch(pieces=[later_piece], artist=later_artist)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Submission.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 2)
        submission.refresh_from_db()
        self.assertEqual(submission.batch_id, original_batch_id)
        self.assertEqual(submission.artist.pronouns, "they/them")
        self.assertEqual(submission.short_bio, "A short bio for this artist.")
        self.assertEqual(submission.socials, "@artist")
        self.assertEqual(submission.country_origin, "DK")
        self.assertEqual(submission.countries_residence, ["DE"])
        self.assertFalse(submission.submitted_before)
        self.assertTrue(submission.featured_before)
        self.assertEqual(submission.message_to_editors, "Please consider both pieces.")
        self.assertEqual(submission.votes.count(), 1)
        self.assertEqual(submission.staff_comments.count(), 1)
        self.assertEqual(list(submission.tags.values_list("name", flat=True)), ["shortlist"])
        self.assertEqual(list(submission.works.values_list("position", "title")), [
            (1, "First Piece"), (2, "Second Piece"),
        ])
        new_submission = Submission.objects.get(pk=response.data["submission"]["id"])
        self.assertNotEqual(new_submission.pk, submission.pk)
        self.assertNotEqual(new_submission.batch_id, original_batch_id)
        self.assertEqual(new_submission.artist.pronouns, "she/her")
        self.assertEqual(new_submission.short_bio, "A newer bio for the same artist.")
        self.assertEqual(new_submission.message_to_editors, "A note for the later work.")
        self.assertEqual(new_submission.works.get().links.get().name, "Draft")
        self.assertEqual(new_submission.votes.count(), 0)
        self.assertEqual(new_submission.tags.count(), 0)
        self.assertEqual(new_submission.staff_comments.count(), 0)
        self.assertEqual(response.data["batch_id"], str(new_submission.batch_id))
        self.assertEqual([work["title"] for work in response.data["submission"]["works"]], [
            "Later Piece",
        ])
        self.assertEqual(response.data["submission"]["tags"], [])
        self.assertEqual(response.data["submission"]["vote_counts"]["total"], 0)
        self.assertNotIn("Review note", str(response.data))
        self.assertEqual([work.title for work in receipt.call_args.args[1]], ["Later Piece"])
        self.assertEqual(receipt.call_args.kwargs, {})

        self.client.force_authenticate(reviewer)
        export = self.client.get("/api/downloads/excel/")
        self.assertEqual(export.status_code, 200)
        worksheet = load_workbook(BytesIO(export.content))["Submissions"]
        headers = [cell.value for cell in worksheet[1]]
        rows = {
            row["Submission ID"]: row
            for row in (dict(zip(headers, values)) for values in worksheet.iter_rows(min_row=2, values_only=True))
        }
        self.assertEqual(set(rows), {submission.pk, new_submission.pk})
        self.assertEqual(rows[submission.pk]["Piece Titles"], "First Piece, Second Piece")
        self.assertEqual(rows[submission.pk]["Yes Votes"], 1)
        self.assertEqual(rows[new_submission.pk]["Piece Titles"], "Later Piece")
        self.assertEqual(rows[new_submission.pk]["Yes Votes"], 0)

    def test_same_email_with_different_artist_name_starts_new_submission(self):
        with patch("submissions.api.submission_views.send_batch_receipt"):
            first = self.post_batch(pieces=[self.pieces[1]])
            second = self.post_batch(pieces=[self.pieces[1]], artist={**self.artist, "artist_name": "Another Artist"})
        self.assertEqual((first.status_code, second.status_code), (201, 201))
        self.assertEqual(Submission.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 2)

    def test_same_artist_name_with_different_email_starts_new_submission(self):
        with patch("submissions.api.submission_views.send_batch_receipt"):
            first = self.post_batch(pieces=[self.pieces[1]])
            second = self.post_batch(pieces=[self.pieces[1]], artist={**self.artist, "email": "other@example.com"})
        self.assertEqual((first.status_code, second.status_code), (201, 201))
        self.assertEqual(Submission.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 2)

    def test_single_work_endpoint_creates_separate_submission(self):
        with patch("submissions.api.submission_views.send_batch_receipt"):
            first = self.post_batch(pieces=[self.pieces[1]])
        self.assertEqual(first.status_code, 201)
        payload = {
            **self.artist,
            "title": "Later single work",
            "submission_type": "poetry",
            "description": "A new piece for the same artist.",
            "language": "English",
            "published_elsewhere": False,
            "text_links": ["https://example.com/later-poem"],
        }
        with patch("submissions.api.submission_views.send_submission_receipt") as receipt:
            response = self.client.post("/api/submissions/", payload, format="multipart", REMOTE_ADDR="198.51.100.231")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Submission.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 2)
        self.assertNotEqual(response.data["id"], first.data["submission"]["id"])
        self.assertEqual([work["title"] for work in response.data["works"]], ["Later single work"])
        self.assertEqual(Work.objects.get(submission_id=response.data["id"]).position, 1)
        receipt.assert_called_once()
        self.assertEqual(receipt.call_args.args[0].pk, response.data["id"])

    def test_invalid_second_piece_creates_nothing(self):
        pieces = [self.pieces[0], {**self.pieces[1], "title": "No"}]
        response = self.post_batch(pieces=pieces)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Submission.objects.exists())
        self.assertFalse(Work.objects.exists())

    def test_named_links_are_saved_with_their_names(self):
        pieces = [{**self.pieces[0], "named_links": [
            {"name": "  Google Doc  ", "url": "https://docs.google.com/document/d/example/edit"},
            {"name": "Video preview", "url": "https://example.com/video"},
        ]}]
        with patch("submissions.api.submission_views.send_batch_receipt"):
            response = self.post_batch(pieces=pieces)
        self.assertEqual(response.status_code, 201)
        links = Work.objects.get().links.order_by("id")
        self.assertEqual(list(links.values_list("name", "url")), [
            ("Google Doc", "https://docs.google.com/document/d/example/edit"),
            ("Video preview", "https://example.com/video"),
        ])
        self.assertEqual(response.data["submission"]["works"][0]["links"][0]["name"], "Google Doc")
        reviewer = get_user_model().objects.create_user(username="link-reviewer", password="test-password", is_staff=True)
        self.client.force_authenticate(reviewer)
        export = self.client.get("/api/downloads/excel/")
        workbook = load_workbook(BytesIO(export.content))
        self.assertEqual(workbook["Links"]["E2"].value, "Google Doc")
        self.assertEqual(workbook["Links"]["F2"].value, "https://docs.google.com/document/d/example/edit")

    def test_named_links_reject_private_urls_and_incomplete_entries(self):
        for link in (
            {"name": "Local", "url": "https://localhost/private"},
            {"name": "Insecure", "url": "http://example.com/work"},
            {"name": "", "url": "https://example.com/work"},
        ):
            with self.subTest(link=link):
                response = self.post_batch(pieces=[{**self.pieces[0], "named_links": [link]}])
                self.assertEqual(response.status_code, 400)
                self.assertFalse(Submission.objects.exists())

    def test_rejects_publication_without_source(self):
        pieces = [{**self.pieces[1], "published_where": ""}]
        response = self.post_batch(pieces=pieces)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Submission.objects.exists())

    @override_settings(SUBMISSION_MAX_TOTAL_FILES_BYTES=10)
    def test_batch_total_upload_limit(self):
        upload = SimpleUploadedFile("poem.pdf", b"%PDF-1.4\ncontent", content_type="application/pdf")
        response = self.post_batch(submission_0_text_files=upload)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Submission.objects.exists())

    def test_png_is_accepted_as_visual(self):
        png = SimpleUploadedFile(
            "art.png",
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\x0dIHDR" + b"\x00" * 20,
            content_type="image/png",
        )
        with patch("submissions.api.submission_views.send_batch_receipt"):
            response = self.post_batch(submission_0_visuals=png)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Work.objects.get(position=1).documents.first().content_type, "image/png")

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        SUBMISSION_EMAIL_FROM="submissions@ragezine.com",
    )
    def test_batch_sends_one_receipt_with_submission_id(self):
        upload = SimpleUploadedFile("poem.pdf", b"%PDF-1.4\ncontent", content_type="application/pdf")
        response = self.post_batch(submission_0_text_files=upload)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["artist@example.com"])
        self.assertEqual(mail.outbox[0].from_email, "submissions@ragezine.com")
        self.assertIn(f"Submission ID: {response.data['submission']['id']}", mail.outbox[0].body)
        self.assertNotIn("First Piece", mail.outbox[0].body)
        self.assertNotIn("Second Piece", mail.outbox[0].body)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        SUBMISSION_EMAIL_FROM="submissions@ragezine.com",
    )
    def test_later_receipt_uses_new_reference(self):
        first = self.post_batch(pieces=[self.pieces[1]])
        later = {**self.pieces[1], "title": "Later Piece"}
        second = self.post_batch(pieces=[later])
        self.assertEqual((first.status_code, second.status_code), (201, 201))
        self.assertEqual(len(mail.outbox), 2)
        self.assertIn(f"Submission ID: {second.data['submission']['id']}", mail.outbox[1].body)
        self.assertNotIn("Later Piece", mail.outbox[1].body)
        self.assertNotIn("Second Piece", mail.outbox[1].body)
        self.assertNotEqual(first.data["submission"]["id"], second.data["submission"]["id"])

    def test_vote_and_export_cover_the_whole_submission(self):
        upload = SimpleUploadedFile("poem.pdf", b"%PDF-1.4\ncontent", content_type="application/pdf")
        with patch("submissions.api.submission_views.send_batch_receipt"):
            self.assertEqual(self.post_batch(submission_0_text_files=upload).status_code, 201)
        submission = Submission.objects.get()
        reviewer = get_user_model().objects.create_user(username="reviewer", password="test-password", is_staff=True)
        SubmissionVote.objects.create(submission=submission, voter=reviewer, choice="yes")
        SubmissionComment.objects.create(submission=submission, author=reviewer, author_name="reviewer", body="Read both pieces")
        self.client.force_authenticate(reviewer)

        detail = self.client.get(f"/api/submissions/{submission.pk}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual([work["title"] for work in detail.data["works"]], ["First Piece", "Second Piece"])
        self.assertEqual(detail.data["vote_counts"]["yes"], 1)

        export = self.client.get("/api/downloads/excel/")
        self.assertEqual(export.status_code, 200)
        workbook = load_workbook(BytesIO(export.content))
        self.assertEqual(workbook["Poetry"]["E2"].value, "First Piece")
        self.assertEqual(workbook["Other"]["E2"].value, "Second Piece")
        self.assertEqual(workbook["Poetry"]["A2"].value, submission.pk)
        self.assertEqual(workbook["Other"]["A2"].value, submission.pk)
        overview = workbook["Submissions"]
        overview_row = dict(zip((cell.value for cell in overview[1]), (cell.value for cell in overview[2])))
        self.assertEqual(overview_row["Artist ID"], submission.artist_id)
        self.assertEqual(overview_row["Piece Count"], 2)
        self.assertEqual(overview_row["Piece Titles"], "First Piece, Second Piece")
        self.assertEqual(overview_row["Yes Votes"], 1)
        self.assertEqual(workbook["Files"]["C2"].value, "First Piece")
        self.assertEqual(workbook["Files"]["E2"].value, "poem.pdf")
        self.assertEqual(workbook["Links"]["C2"].value, "Second Piece")
        self.assertEqual(workbook["Comments"]["D2"].value, "Read both pieces")
