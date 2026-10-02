from rest_framework import serializers
from django.urls import reverse
from .models import Submission, SubmissionDocument
import pycountry
from submissions.utils import sanitize_multiline, sanitize_single_line

PRONOUN_VALUES = {
    "she/her",
    "he/him",
    "they/them",
    "she/they",
    "he/they",
    "xe/xem",
    "ze/zir",
    "any",
    "prefer-not",
    "other",
}

VALID_LANGUAGES = {
    "English",
    "Spanish",
    "Danish",
    "French",
    "German",
    "Italian",
    "Portuguese",
    "Other",
}

VALID_SUBMISSION_TYPES = {choice for choice, _ in Submission.SubmissionType.choices}

def country_name(code):
    country = pycountry.countries.get(alpha_2=code)
    return country.name if country else code


def is_valid_country_code(code):
    return pycountry.countries.get(alpha_2=code) is not None



class SubmissionDocumentSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    def get_download_url(self, obj):
        url = reverse("downloads-document", args=[obj.pk])
        request = self.context.get("request")
        return request.build_absolute_uri(url) if request else url

    class Meta:
        model = SubmissionDocument
        fields = [
            "id",
            "document_type",
            "download_url",
            "original_filename",
            "content_type",
            "size",
            "created_at",
        ]


class SubmissionSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True, allow_blank=False)

    countries_residence_names = serializers.SerializerMethodField()
    countries_residence = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
    )
    documents = SubmissionDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = Submission
        fields = [
            "id",
            "title",
            "year",
            "description",
            "submission_type",
            "artist_name",
            "pronouns",
            "short_bio",
            "socials",
            "email",
            "country_origin",
            "countries_residence",
            "countries_residence_names",
            "language",
            "allow_translation",
            "documents",
            "created_at",
            "updated_at",
        ]
    def get_countries_residence_names(self, obj):
        return [country_name(code) for code in obj.countries_residence]

    def validate_title(self, value):
        value = sanitize_single_line(value)
        if len(value) <= 2:
            raise serializers.ValidationError(
                "Title must be longer than 2 characters."
            )
        return value

    def validate_year(self, value):
        return sanitize_single_line(value)

    def validate_description(self, value):
        value = sanitize_multiline(value)
        if len(value) < 10:
            raise serializers.ValidationError(
                "Description must contain at least one short sentence."
            )
        return value

    def validate_submission_type(self, value):
        value = sanitize_single_line(value).lower()
        if value not in VALID_SUBMISSION_TYPES:
            raise serializers.ValidationError(
                "Submission type must be one of the allowed options."
            )
        return value

    def validate_artist_name(self, value):
        value = sanitize_single_line(value)
        if len(value) < 2:
            raise serializers.ValidationError(
                "Artist name must be at least 2 characters long."
            )
        return value

    def validate_pronouns(self, value):
        value = sanitize_single_line(value).lower()
        if value not in PRONOUN_VALUES:
            raise serializers.ValidationError(
                "Pronouns must be one of the allowed options."
            )
        return value

    def validate_short_bio(self, value):
        value = sanitize_multiline(value)
        if len(value) < 10:
            raise serializers.ValidationError(
                "Short bio must contain at least one short sentence."
            )
        return value

    def validate_socials(self, value):
        sanitized = sanitize_multiline(value)
        if not sanitized:
            return ""

        socials = []
        for entry in sanitized.split("\n"):
            entry = sanitize_single_line(entry)
            if entry and entry not in socials:
                socials.append(entry)
        return "\n".join(socials)

    def validate_email(self, value):
        value = sanitize_single_line(value).lower()
        if not value:
            raise serializers.ValidationError("Email is required.")
        return value

    def validate_country_origin(self, value):
        value = sanitize_single_line(value).upper()
        if not is_valid_country_code(value):
            raise serializers.ValidationError(
                "countries_origin must be one valid country name in English."
            )
        return value

    def validate_countries_residence(self, value):
        sanitized = []
        for country in value:
            country = sanitize_single_line(country).upper()
            if not is_valid_country_code(country):
                raise serializers.ValidationError(
                    f"'{country}' is not a valid residence country name in English."
                )
            if country not in sanitized:
                sanitized.append(country)
        return sanitized

    def validate_language(self, value):
        value = sanitize_single_line(value).title()
        if value not in VALID_LANGUAGES:
            raise serializers.ValidationError(
                "Language must be one of the allowed options."
            )
        return value

    def validate(self, attrs):
        request = self.context.get("request")

        language = attrs.get("language", "English")
        allow_translation = attrs.get("allow_translation", False)

        text_files = []
        visuals = []
        if request:
            text_files = request.FILES.getlist("text_files")
            visuals = request.FILES.getlist("visuals")

        # Rule: there must be a text file or at least one visual
        if not text_files and not visuals:
            raise serializers.ValidationError(
                "A submission must include a text file or at least one visual."
            )

        # Rule: if language is other than English, allow_translation must be true
        if language != "English" and not allow_translation:
            raise serializers.ValidationError(
                {
                    "allow_translation": (
                        "When the language is not English a translation must be allowed."
                    )
                }
            )

        return attrs
