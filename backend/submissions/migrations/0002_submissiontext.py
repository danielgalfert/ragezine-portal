from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("submissions", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="SubmissionText",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("file", models.FileField(upload_to="submissions/texts/")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "submission",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="texts",
                        to="submissions.submission",
                    ),
                ),
            ],
            options={
                "ordering": ["created_at"],
            },
        ),
    ]
