from django.contrib import admin
from django.contrib.admin.widgets import AdminFileWidget
from django.db import models
from django.urls import reverse

from .models import Submission, SubmissionDocument


class _ProtectedFileLink:
    def __init__(self, document):
        self.url = reverse("downloads-document", args=[document.pk])
        self.name = document.original_filename or document.file.name.rsplit("/", 1)[-1]

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


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    inlines = [SubmissionDocumentInline]


@admin.register(SubmissionDocument)
class SubmissionDocumentAdmin(ProtectedDocumentFileAdminMixin, admin.ModelAdmin):
    list_display = (
        "id",
        "submission",
        "document_type",
        "original_filename",
        "content_type",
        "size",
        "created_at",
    )
    list_filter = ("document_type", "content_type", "created_at")
    search_fields = ("original_filename", "file", "submission__artist_name", "submission__title")
