import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.migrations.exceptions import IrreversibleError
from django.db.models import Count


def move_existing_submissions(apps, schema_editor):
    Artist = apps.get_model("submissions", "Artist")
    Submission = apps.get_model("submissions", "Submission")
    Work = apps.get_model("submissions", "Work")
    Document = apps.get_model("submissions", "SubmissionDocument")
    Link = apps.get_model("submissions", "SubmissionLink")
    database = schema_editor.connection.alias

    for submission in Submission.objects.using(database).all().iterator():
        artist = Artist.objects.using(database).create(
            artist_name=submission.artist_name,
            pronouns=submission.pronouns,
            email=submission.email.strip().lower(),
            short_bio=submission.short_bio,
            socials=submission.socials,
            country_origin=submission.country_origin,
            countries_residence=submission.countries_residence,
            message_to_editors=submission.message_to_editors,
            submitted_before=submission.submitted_before,
            featured_before=submission.featured_before,
        )
        Artist.objects.using(database).filter(pk=artist.pk).update(created_at=submission.created_at)
        Submission.objects.using(database).filter(pk=submission.pk).update(artist=artist)
        work = Work.objects.using(database).create(
            submission=submission,
            position=1,
            title=submission.title,
            year=submission.year,
            description=submission.description,
            submission_type=submission.submission_type,
            language=submission.language,
            published_elsewhere=submission.published_elsewhere,
            published_where=submission.published_where,
            anything_else=submission.anything_else,
        )
        Work.objects.using(database).filter(pk=work.pk).update(
            created_at=submission.created_at, updated_at=submission.updated_at
        )
        Document.objects.using(database).filter(submission_id=submission.pk).update(work_id=work.pk)
        Link.objects.using(database).filter(submission_id=submission.pk).update(work_id=work.pk)


def guard_reverse_migration(apps, schema_editor):
    Work = apps.get_model("submissions", "Work")
    database = schema_editor.connection.alias
    if Work.objects.using(database).values("submission_id").annotate(total=Count("id")).filter(total__gt=1).exists():
        raise IrreversibleError("A submission has several works. Export or move them before reversing this migration.")


class Migration(migrations.Migration):
    dependencies = [("submissions", "0015_submission_batch_fields")]

    operations = [
        migrations.CreateModel(
            name="Artist",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("artist_name", models.CharField(max_length=255)),
                ("pronouns", models.CharField(max_length=500)),
                ("email", models.EmailField(db_index=True, max_length=254)),
                ("short_bio", models.TextField()),
                ("socials", models.CharField(blank=True, max_length=500)),
                ("country_origin", models.TextField()),
                ("countries_residence", settings.DATABASE_HANDLER.residence_field()),
                ("message_to_editors", models.TextField(blank=True)),
                ("submitted_before", models.BooleanField(blank=True, null=True)),
                ("featured_before", models.BooleanField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.AddField(
            model_name="submission", name="artist",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="submissions", to="submissions.artist"),
        ),
        migrations.CreateModel(
            name="Work",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("position", models.PositiveSmallIntegerField()),
                ("title", models.CharField(max_length=255)),
                ("year", models.CharField(blank=True, max_length=32)),
                ("description", models.TextField(blank=True)),
                ("submission_type", models.CharField(choices=[("poetry", "Poetry"), ("visual_art", "Visual art"), ("short_form_writing", "Short form writing"), ("long_form_writing", "Long form writing"), ("other", "Other")], max_length=32)),
                ("language", models.CharField(default="English", max_length=64)),
                ("published_elsewhere", models.BooleanField(blank=True, null=True)),
                ("published_where", models.TextField(blank=True)),
                ("anything_else", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("submission", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="works", to="submissions.submission")),
            ],
            options={"ordering": ["position", "id"], "constraints": [models.UniqueConstraint(fields=("submission", "position"), name="one_position_per_submission")]},
        ),
        migrations.AddField(
            model_name="submissiondocument", name="work",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="documents", to="submissions.work"),
        ),
        migrations.AddField(
            model_name="submissionlink", name="work",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="links", to="submissions.work"),
        ),
        migrations.RunPython(move_existing_submissions, guard_reverse_migration),
    ]
