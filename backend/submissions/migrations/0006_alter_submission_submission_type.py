from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("submissions", "0005_alter_submission_email"),
    ]

    operations = [
        migrations.AlterField(
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
                max_length=32,
            ),
        ),
    ]
