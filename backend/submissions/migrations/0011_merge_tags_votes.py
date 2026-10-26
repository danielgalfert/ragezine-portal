from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("submissions", "0009_tag_submission_tags"),
        (
            "submissions",
            "0010_remove_submissionvote_submission_vote_comment_matches_choice_and_more",
        ),
    ]

    operations = []
