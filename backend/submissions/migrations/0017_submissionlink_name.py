from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("submissions", "0016_artist_submission_work")]

    operations = [
        migrations.AddField(
            model_name="submissionlink",
            name="name",
            field=models.CharField(blank=True, max_length=120),
        ),
    ]
