from django.contrib import admin

from .models import Submission, SubmissionVisual


class SubmissionVisualInline(admin.TabularInline):
    model = SubmissionVisual
    extra = 0


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("id", "artist_name", "title", "language", "created_at")
    list_filter = ("language", "allow_translation", "created_at")
    search_fields = ("artist_name", "title", "pronouns", "countries_origin")
    inlines = [SubmissionVisualInline]


@admin.register(SubmissionVisual)
class SubmissionVisualAdmin(admin.ModelAdmin):
    list_display = ("id", "submission", "image", "created_at")
    list_filter = ("created_at",)
