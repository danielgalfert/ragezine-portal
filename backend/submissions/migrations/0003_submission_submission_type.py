from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("submissions", "0002_submissiontext"),
    ]

    operations = [
        migrations.AddField(
            model_name="submission",
            name="submission_type",
            field=models.CharField(
                choices=[
                    ("poetry", "Poetry"),
                    ("visual_art", "Visual art"),
                    ("short_form_writing", "Short form writing"),
                    ("long_form_writing", "Long form writing"),
                    ("other", "Other"),
                ],
                default="other",
                max_length=32,
            ),
            preserve_default=False,
        ),
    ]
