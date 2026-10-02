import os

import django.db.models.deletion
import submissions.models
from django.db import migrations, models


def migrate_existing_documents(apps, schema_editor):
    Submission = apps.get_model("submissions", "Submission")
    SubmissionText = apps.get_model("submissions", "SubmissionText")
    SubmissionVisual = apps.get_model("submissions", "SubmissionVisual")
    SubmissionDocument = apps.get_model("submissions", "SubmissionDocument")

    documents = []

    for submission in Submission.objects.exclude(text_file="").exclude(text_file__isnull=True):
        documents.append(
            SubmissionDocument(
                submission_id=submission.id,
                document_type="text",
                file=submission.text_file,
                original_filename=os.path.basename(submission.text_file.name),
                size=0,
                created_at=submission.created_at,
            )
        )

    for text in SubmissionText.objects.all():
        documents.append(
            SubmissionDocument(
                submission_id=text.submission_id,
                document_type="text",
                file=text.file,
                original_filename=os.path.basename(text.file.name),
                size=0,
                created_at=text.created_at,
            )
        )

    for visual in SubmissionVisual.objects.all():
        documents.append(
            SubmissionDocument(
                submission_id=visual.submission_id,
                document_type="visual",
                file=visual.image,
                original_filename=os.path.basename(visual.image.name),
                size=0,
                created_at=visual.created_at,
            )
        )

    SubmissionDocument.objects.bulk_create(documents)


class Migration(migrations.Migration):

    dependencies = [
        ("submissions", "0006_alter_submission_submission_type"),
    ]

    operations = [
        migrations.CreateModel(
            name="SubmissionDocument",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "document_type",
                    models.CharField(
                        choices=[("text", "Text"), ("visual", "Visual")],
                        max_length=16,
                    ),
                ),
                (
                    "file",
                    models.FileField(
                        upload_to=submissions.models.submission_document_upload_path,
                    ),
                ),
                ("original_filename", models.CharField(blank=True, max_length=255)),
                ("content_type", models.CharField(blank=True, max_length=255)),
                ("size", models.PositiveBigIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "submission",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="documents",
                        to="submissions.submission",
                    ),
                ),
            ],
            options={
                "ordering": ["created_at"],
            },
        ),
        migrations.RunPython(migrate_existing_documents, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="submission",
            name="text_file",
        ),
        migrations.DeleteModel(
            name="SubmissionText",
        ),
        migrations.DeleteModel(
            name="SubmissionVisual",
        ),
        migrations.AddIndex(
            model_name="submissiondocument",
            index=models.Index(
                fields=["submission", "document_type"],
                name="submission__submiss_6825b9_idx",
            ),
        ),
    ]
