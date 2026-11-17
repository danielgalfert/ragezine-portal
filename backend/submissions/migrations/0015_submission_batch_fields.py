from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("submissions", "0014_alter_submission_pronouns"),
    ]

    operations = [
        migrations.AddField("submission", "anything_else", models.TextField(blank=True)),
        migrations.AddField("submission", "batch_id", models.UUIDField(blank=True, db_index=True, null=True)),
        migrations.AddField("submission", "batch_position", models.PositiveSmallIntegerField(blank=True, null=True)),
        migrations.AddField("submission", "featured_before", models.BooleanField(blank=True, null=True)),
        migrations.AddField("submission", "message_to_editors", models.TextField(blank=True)),
        migrations.AddField("submission", "published_elsewhere", models.BooleanField(blank=True, null=True)),
        migrations.AddField("submission", "published_where", models.TextField(blank=True)),
        migrations.AddField("submission", "submitted_before", models.BooleanField(blank=True, null=True)),
        migrations.AlterField(
            "submissionlink",
            "link_type",
            models.CharField(
                choices=[
                    ("text", "Text"),
                    ("visual", "Visual"),
                    ("video", "Video"),
                    ("other", "Third-party"),
                ],
                max_length=16,
            ),
        ),
    ]
