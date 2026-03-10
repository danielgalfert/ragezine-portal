from rest_framework import serializers
from .models import Submission, SubmissionVisual
import pycountry


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

def country_name(code):
    country = pycountry.countries.get(alpha_2=code)
    return country.name if country else code


def is_valid_country_code(code):
    return pycountry.countries.get(alpha_2=code) is not None



class SubmissionVisualSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubmissionVisual
        fields = ["id", "image", "created_at"]


class SubmissionSerializer(serializers.ModelSerializer):

    countries_residence_names = serializers.SerializerMethodField()
    countries_residence = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
    )
    visuals = SubmissionVisualSerializer(many=True, read_only=True)

    class Meta:
        model = Submission
        fields = [
            "id",
            "title",
            "year",
            "description",
            "artist_name",
            "pronouns",
            "short_bio",
            "socials",
            "country_origin",
            "countries_residence",
            "countries_residence_names",
            "language",
            "allow_translation",
            "text_file",
            "visuals",
            "created_at",
            "updated_at",
        ]
    def get_countries_residence_names(self, obj):
        return [country_name(code) for code in obj.countries_residence]

    def validate_title(self, value):
        value = value.strip()
        if len(value) <= 2:
            raise serializers.ValidationError(
                "Title must be longer than 2 characters."
            )
        return value

    def validate_description(self, value):
        value = value.strip()
        if len(value) < 10:
            raise serializers.ValidationError(
                "Description must contain at least one short sentence."
            )
        return value

    def validate_pronouns(self, value):
        if value not in PRONOUN_VALUES:
            raise serializers.ValidationError(
                "Pronouns must be one of the allowed options."
            )
        return value
    
    def validate_country_origin(self, value):
        value = value.strip()
        if not is_valid_country_code(value):
            raise serializers.ValidationError(
                "countries_origin must be one valid country name in English."
            )
        return value

    def validate_countries_residence(self, value):
        for country in value:
            if not is_valid_country_code(country):
                raise serializers.ValidationError(
                    f"'{country}' is not a valid residence country name in English."
                )
        return value

    def validate(self, attrs):
        request = self.context.get("request")

        text_file = attrs.get("text_file")
        language = attrs.get("language", "English")
        allow_translation = attrs.get("allow_translation", False)

        visuals = []
        if request:
            visuals = request.FILES.getlist("visuals")

        # Rule: there must be a text file or at least one visual
        if not text_file and not visuals:
            raise serializers.ValidationError(
                "A submission must include a text file or at least one visual."
            )

        # Rule: if language is other than English, allow_translation must be true
        if language != "English" and not allow_translation:
            raise serializers.ValidationError(
                {
                    "allow_translation": (
                        "allow_translation must be true when the language is not English."
                    )
                }
            )

        return attrs