from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("submissions", "0019_alter_submission_language_alter_work_language"),
    ]

    operations = [
        migrations.AlterField(
            model_name="submission",
            name="volume",
            field=models.IntegerField(default=4),
        ),
    ]
