from django.db import models


class Submission(models.Model):
    title = models.CharField(max_length=255)
    year = models.CharField(max_length=32, blank=True)
    description = models.TextField(blank=True)

    artist_name = models.CharField(max_length=255)
    pronouns = models.CharField(max_length=128)
    short_bio = models.TextField()
    socials = models.CharField(max_length=500, blank=True)

    countries_origin = models.TextField()
    countries_residence = models.TextField(blank=True)

    language = models.CharField(max_length=64, default="English")
    allow_translation = models.BooleanField(default=False)

    text_file = models.FileField(upload_to="submissions/texts/", blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.artist_name} — {self.title}"


class SubmissionVisual(models.Model):
    submission = models.ForeignKey(
        Submission,
        on_delete=models.CASCADE,
        related_name="visuals",
    )
    image = models.FileField(upload_to="submissions/visuals/")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Visual for {self.submission_id}: {self.image.name}"
