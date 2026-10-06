from django.db import models
from django.conf import settings
from uuid import uuid4


VOLUME_NUMBER = 3


def submission_document_upload_path(instance, filename):
    document_type = instance.document_type or SubmissionDocument.DocumentType.TEXT
    folder = (
        "visuals"
        if document_type == SubmissionDocument.DocumentType.VISUAL
        else "texts"
    )
    return f"submissions/{folder}/{instance.submission_id}/{uuid4().hex}-{filename}"


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

    artist_name = models.CharField(max_length=255)
    pronouns = models.CharField(max_length=128)
    short_bio = models.TextField()

    socials = models.CharField(max_length=500, blank=True)
    email = models.EmailField()

    country_origin = models.TextField()
    countries_residence = settings.DATABASE_HANDLER.residence_field()

    language = models.CharField(max_length=64, default="English")
    allow_translation = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.artist_name} — {self.title}"


class SubmissionDocumentQuerySet(models.QuerySet):
    def texts(self):
        return self.filter(document_type=SubmissionDocument.DocumentType.TEXT)

    def visuals(self):
        return self.filter(document_type=SubmissionDocument.DocumentType.VISUAL)


class SubmissionDocument(models.Model):
    class DocumentType(models.TextChoices):
        TEXT = "text", "Text"
        VISUAL = "visual", "Visual"

    submission = models.ForeignKey(
        Submission,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    document_type = models.CharField(max_length=16, choices=DocumentType.choices)
    file = models.FileField(upload_to=submission_document_upload_path)
    original_filename = models.CharField(max_length=255, blank=True)
    content_type = models.CharField(max_length=255, blank=True)
    size = models.PositiveBigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = SubmissionDocumentQuerySet.as_manager()

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(
                fields=["submission", "document_type"],
                name="submission__submiss_6825b9_idx",
            ),
        ]

    @classmethod
    def create_from_upload(cls, submission, uploaded_file, document_type):
        return cls.objects.create(
            submission=submission,
            document_type=document_type,
            file=uploaded_file,
            original_filename=uploaded_file.name or "",
            content_type=getattr(uploaded_file, "content_type", "") or "",
            size=getattr(uploaded_file, "size", 0) or 0,
        )

    def __str__(self):
        return (
            f"{self.get_document_type_display()} "
            f"for {self.submission_id}: {self.file.name}"
        )
