from django.contrib import admin
from django.contrib.admin.widgets import AdminFileWidget
from django.db import models
from django.urls import reverse

from .models import Artist, Submission, SubmissionDocument, Work
from .filenames import submission_document_filename


class _ProtectedFileLink:
    def __init__(self, document):
        self.url = reverse("downloads-document", args=[document.pk])
        self.name = submission_document_filename(document)

    def __str__(self):
        return self.name


class ProtectedAdminFileWidget(AdminFileWidget):
    def is_initial(self, value):
        document = getattr(value, "instance", None)
        return bool(value and getattr(value, "name", None) and getattr(document, "pk", None))

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        if context["widget"]["is_initial"] and value.instance.pk:
            context["widget"]["value"] = _ProtectedFileLink(value.instance)
        return context


class ProtectedDocumentFileAdminMixin:
    formfield_overrides = {models.FileField: {"widget": ProtectedAdminFileWidget}}


class SubmissionDocumentInline(ProtectedDocumentFileAdminMixin, admin.TabularInline):
    model = SubmissionDocument
    extra = 0
    readonly_fields = ("original_filename", "content_type", "size", "created_at")


class WorkInline(admin.TabularInline):
    model = Work
    extra = 0
    show_change_link = True


@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = ("id", "artist_name", "email", "created_at")
    search_fields = ("artist_name", "email")


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("id", "artist", "created_at", "volume")
    inlines = [WorkInline]


@admin.register(Work)
class WorkAdmin(admin.ModelAdmin):
    list_display = ("id", "submission", "position", "title", "submission_type", "created_at")
    list_filter = ("submission_type",)
    search_fields = ("title", "submission__artist__artist_name", "submission__artist__email")
    inlines = [SubmissionDocumentInline]


@admin.register(SubmissionDocument)
class SubmissionDocumentAdmin(ProtectedDocumentFileAdminMixin, admin.ModelAdmin):
    list_display = (
        "id",
        "submission",
        "document_type",
        "formatted_filename",
        "content_type",
        "size",
        "created_at",
    )
    list_filter = ("document_type", "content_type", "created_at")
    search_fields = ("original_filename", "file", "submission__artist_name", "submission__title")

    @admin.display(description="Filename")
    def formatted_filename(self, document):
        return submission_document_filename(document)
