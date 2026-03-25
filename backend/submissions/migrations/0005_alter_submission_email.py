from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("submissions", "0004_merge_20260322_2222"),
    ]

    operations = [
        migrations.AlterField(
            model_name="submission",
            name="email",
            field=models.EmailField(max_length=254),
        ),
    ]
