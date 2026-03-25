from django.db import models
from django.contrib.postgres.fields import ArrayField


VOLUME_NUMBER = 3

class Submission(models.Model):
    class SubmissionType(models.TextChoices):
        POETRY = "poetry", "Poetry"
        VISUAL_ART = "visual_art", "Visual art"
        SHORT_FORM_WRITING = "short_form_writing", "Short form writing"
        LONG_FORM_WRITING = "long_form_writing", "Long form writing"
        OTHER = "other", "Other"

    title = models.CharField(max_length=255)
    year = models.CharField(max_length=32, blank=True)
    description = models.TextField(blank=True)
    submission_type = models.CharField(
        max_length=32,
        choices=SubmissionType.choices,
    )

    volume = models.IntegerField(default=VOLUME_NUMBER)


    #Personal info
    artist_name = models.CharField(max_length=255)
    pronouns = models.CharField(max_length=128)
    short_bio = models.TextField()


    #Contact info
    socials = models.CharField(max_length=500, blank=True)
    email = models.EmailField()

    country_origin = models.TextField()
    countries_residence = ArrayField(
        base_field=models.CharField(max_length=100),
        default=list,
        blank=True,
    )

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


class SubmissionText(models.Model):
    submission = models.ForeignKey(
        Submission,
        on_delete=models.CASCADE,
        related_name="texts",
    )
    file = models.FileField(upload_to="submissions/texts/")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Text for {self.submission_id}: {self.file.name}"
