from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class ArtistWorkMigrationTests(TransactionTestCase):
    migrate_from = ("submissions", "0015_submission_batch_fields")
    migrate_to = ("submissions", "0016_artist_submission_work")

    def test_existing_submission_becomes_one_artist_and_work(self):
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        old_apps = executor.loader.project_state([self.migrate_from]).apps
        OldSubmission = old_apps.get_model("submissions", "Submission")
        OldLink = old_apps.get_model("submissions", "SubmissionLink")
        old = OldSubmission.objects.create(
            title="An existing piece",
            description="An existing description.",
            submission_type="poetry",
            artist_name="Existing Artist",
            pronouns="they/them",
            short_bio="A short biography.",
            email="Artist@Example.com",
            country_origin="DK",
            countries_residence=["DK"],
        )
        link = OldLink.objects.create(
            submission=old, link_type="text", url="https://example.com/old-work"
        )
        old_created_at = old.created_at

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        new_apps = executor.loader.project_state([self.migrate_to]).apps
        Submission = new_apps.get_model("submissions", "Submission")
        Work = new_apps.get_model("submissions", "Work")
        Link = new_apps.get_model("submissions", "SubmissionLink")
        submission = Submission.objects.get(pk=old.pk)
        work = Work.objects.get(submission_id=old.pk)

        self.assertEqual(submission.artist.artist_name, "Existing Artist")
        self.assertEqual(submission.artist.email, "artist@example.com")
        self.assertEqual(work.title, "An existing piece")
        self.assertEqual(work.created_at, old_created_at)
        self.assertEqual(Link.objects.get(pk=link.pk).work_id, work.pk)
