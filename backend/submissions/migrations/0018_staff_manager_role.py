from django.conf import settings
from django.db import migrations


def grant_existing_staff_manager_role(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    Group = apps.get_model("auth", "Group")
    user_app, user_model = settings.AUTH_USER_MODEL.split(".")
    User = apps.get_model(user_app, user_model)
    database = schema_editor.connection.alias

    content_type, _ = ContentType.objects.using(database).get_or_create(
        app_label="submissions", model="submission"
    )
    delete_permission, _ = Permission.objects.using(database).get_or_create(
        content_type=content_type,
        codename="delete_submission",
        defaults={"name": "Can delete submission"},
    )
    export_permission, _ = Permission.objects.using(database).get_or_create(
        content_type=content_type,
        codename="export_all_submissions",
        defaults={"name": "Can export all submissions"},
    )
    group, _ = Group.objects.using(database).get_or_create(name="Submission Managers")
    group.permissions.add(delete_permission, export_permission)
    for user in User.objects.using(database).filter(is_staff=True).iterator():
        user.groups.add(group)


class Migration(migrations.Migration):
    dependencies = [
        ("submissions", "0017_submissionlink_name"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="submission",
            options={
                "ordering": ["-created_at"],
                "permissions": [("export_all_submissions", "Can export all submissions")],
            },
        ),
        migrations.RunPython(grant_existing_staff_manager_role, migrations.RunPython.noop),
    ]
