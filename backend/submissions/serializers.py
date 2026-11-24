import json
import pycountry
from ipaddress import ip_address
from urllib.parse import urlsplit

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import URLValidator
from django.db.models import Count
from django.urls import reverse
from rest_framework import serializers

from .models import Artist, Submission, SubmissionComment, SubmissionDocument, SubmissionLink, SubmissionVote, Tag, Work
from submissions.preview import preview_kind as get_preview_kind
from submissions.utils import sanitize_multiline, sanitize_single_line
from submissions.utils.uploads import validate_upload

VALID_SUBMISSION_TYPES = {choice for choice, _ in Submission.SubmissionType.choices}
LINK_URL_VALIDATOR = URLValidator(schemes=["https"])


def submitted_links(data, field_name):
    if hasattr(data, "getlist"):
        return data.getlist(field_name)
    value = data.get(field_name, [])
    return value if isinstance(value, list) else [value]


def validate_link_url(value):
    if not isinstance(value, str):
        raise serializers.ValidationError("Enter an HTTPS link.")
    value = sanitize_single_line(value)
    if not value or len(value) > 2048:
        raise serializers.ValidationError("Enter an HTTPS link of at most 2048 characters.")
    try:
        LINK_URL_VALIDATOR(value)
        parsed = urlsplit(value)
        host = (parsed.hostname or "").rstrip(".").lower()
        if parsed.username or parsed.password or host == "localhost" or host.endswith(".localhost"):
            raise ValueError
        try:
            address = ip_address(host)
        except ValueError:
            # A domain name is valid here. The server never fetches the link.
            if host.replace(".", "").isdigit():
                raise ValueError
        else:
            if not address.is_global:
                raise ValueError
    except (DjangoValidationError, ValueError) as error:
        raise serializers.ValidationError("Use a public HTTPS link.") from error
    return value

def country_name(code):
    country = pycountry.countries.get(alpha_2=code)
    return country.name if country else code


def origin_codes(value):
    if isinstance(value, str):
        return [code.strip() for code in value.split(",") if code.strip()]
    return list(value or [])


def is_valid_country_code(code):
    return pycountry.countries.get(alpha_2=code) is not None


class CountryOriginField(serializers.ListField):
    def to_internal_value(self, data):
        if isinstance(data, str):
            data = origin_codes(data)
        return super().to_internal_value(data)

    def to_representation(self, value):
        return super().to_representation(origin_codes(value))


class SubmissionDocumentSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()
    preview_kind = serializers.SerializerMethodField()
    preview_url = serializers.SerializerMethodField()

    def get_download_url(self, obj):
        url = reverse("downloads-document", args=[obj.pk])
        request = self.context.get("request")
        return request.build_absolute_uri(url) if request else url

    def get_preview_kind(self, obj):
        return get_preview_kind(obj)

    def get_preview_url(self, obj):
        if not get_preview_kind(obj):
            return None
        return reverse("preview-document", args=[obj.pk])

    class Meta:
        model = SubmissionDocument
        fields = [
            "id",
            "document_type",
            "download_url",
            "preview_kind",
            "preview_url",
            "original_filename",
            "content_type",
            "size",
            "created_at",
        ]


class SubmissionLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubmissionLink
        fields = ["id", "link_type", "name", "url", "created_at"]


class ArtistSerializer(serializers.ModelSerializer):
    country_origin_names = serializers.SerializerMethodField()
    countries_residence_names = serializers.SerializerMethodField()

    class Meta:
        model = Artist
        fields = [
            "id", "artist_name", "pronouns", "email", "short_bio", "socials",
            "country_origin", "country_origin_names", "countries_residence",
            "countries_residence_names", "message_to_editors", "submitted_before",
            "featured_before", "created_at",
        ]

    def get_country_origin_names(self, obj):
        return [country_name(code) for code in origin_codes(obj.country_origin)]

    def get_countries_residence_names(self, obj):
        return [country_name(code) for code in obj.countries_residence]


class WorkSerializer(serializers.ModelSerializer):
    documents = SubmissionDocumentSerializer(many=True, read_only=True)
    links = SubmissionLinkSerializer(many=True, read_only=True)

    class Meta:
        model = Work
        fields = [
            "id", "position", "title", "submission_type", "year", "description",
            "language", "published_elsewhere", "published_where", "anything_else",
            "documents", "links", "created_at", "updated_at",
        ]


class SubmissionCommentSerializer(serializers.ModelSerializer):
    body = serializers.CharField(max_length=4000, trim_whitespace=True)
    author_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = SubmissionComment
        fields = ["id", "body", "author_id", "author_name", "created_at"]
        read_only_fields = ["id", "author_id", "author_name", "created_at"]

    def validate_body(self, value):
        value = sanitize_multiline(value)
        if not value:
            raise serializers.ValidationError("Enter a comment.")
        return value


class SubmissionVoteInputSerializer(serializers.Serializer):
    choice = serializers.ChoiceField(choices=SubmissionVote.Choice.choices)

    def validate(self, attrs):
        if set(self.initial_data) != {"choice"}:
            raise serializers.ValidationError("Send only a vote choice.")
        return attrs


class SubmissionVoteSerializer(serializers.ModelSerializer):
    voter_name = serializers.SerializerMethodField()

    class Meta:
        model = SubmissionVote
        fields = ["id", "voter_id", "voter_name", "choice", "updated_at"]

    def get_voter_name(self, obj):
        return obj.voter.get_username()


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name"]


class TagNameSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=50)

    def validate_name(self, value):
        name = sanitize_single_line(value).casefold()
        if not name or len(name) > 50:
            raise serializers.ValidationError("Enter a tag of at most 50 characters.")
        if not all(char.isalnum() or char in " -_" for char in name):
            raise serializers.ValidationError("Use letters, numbers, spaces, hyphens, or underscores.")
        return name


class SubmissionSerializer(serializers.ModelSerializer):
    volume = serializers.IntegerField(read_only=True)
    batch_id = serializers.UUIDField(read_only=True)
    batch_position = serializers.IntegerField(read_only=True)
    email = serializers.EmailField(required=True, allow_blank=False)
    description = serializers.CharField(required=False, allow_blank=True, max_length=10000)
    short_bio = serializers.CharField(max_length=4000)
    message_to_editors = serializers.CharField(required=False, allow_blank=True, max_length=4000)
    published_where = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    anything_else = serializers.CharField(required=False, allow_blank=True, max_length=4000)
    country_origin = CountryOriginField(
        child=serializers.CharField(max_length=2),
        allow_empty=False,
        max_length=20,
    )

    countries_residence_names = serializers.SerializerMethodField()
    country_origin_name = serializers.SerializerMethodField()
    country_origin_names = serializers.SerializerMethodField()
    countries_residence = serializers.ListField(
        child=serializers.CharField(max_length=2),
        required=False,
        allow_empty=True,
        max_length=20,
    )
    documents = SubmissionDocumentSerializer(many=True, read_only=True)
    links = SubmissionLinkSerializer(many=True, read_only=True)
    vote_counts = serializers.SerializerMethodField()
    tags = TagSerializer(many=True, read_only=True)
    staff_search_text = serializers.SerializerMethodField()
    artist = ArtistSerializer(read_only=True)
    works = WorkSerializer(many=True, read_only=True)

    class Meta:
        model = Submission
        fields = [
            "id",
            "title",
            "year",
            "description",
            "submission_type",
            "volume",
            "artist",
            "works",
            "batch_id",
            "batch_position",
            "artist_name",
            "pronouns",
            "short_bio",
            "message_to_editors",
            "submitted_before",
            "featured_before",
            "socials",
            "email",
            "country_origin",
            "country_origin_name",
            "country_origin_names",
            "countries_residence",
            "countries_residence_names",
            "language",
            "published_elsewhere",
            "published_where",
            "anything_else",
            "allow_translation",
            "documents",
            "links",
            "vote_counts",
            "tags",
            "staff_search_text",
            "created_at",
            "updated_at",
        ]

    def get_vote_counts(self, obj):
        counts = {choice: 0 for choice in SubmissionVote.Choice.values}
        annotated = {
            "yes": getattr(obj, "yes_vote_count", None),
            "no": getattr(obj, "no_vote_count", None),
            "see_comment": getattr(obj, "see_comment_vote_count", None),
        }
        if all(value is not None for value in annotated.values()):
            counts.update(annotated)
        else:
            for row in obj.votes.values("choice").annotate(count=Count("id")):
                counts[row["choice"]] = row["count"]
        counts["total"] = sum(counts.values())
        return counts

    def get_staff_search_text(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_staff:
            return ""
        return " ".join(comment.body for comment in obj.staff_comments.all())

    def get_countries_residence_names(self, obj):
        return [country_name(code) for code in obj.countries_residence]

    def get_country_origin_name(self, obj):
        return ", ".join(self.get_country_origin_names(obj))

    def get_country_origin_names(self, obj):
        return [country_name(code) for code in origin_codes(obj.country_origin)]

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
        tags = [sanitize_single_line(tag) for tag in value.split(",")]
        if not tags or len(tags) > 10 or any(
            not tag or len(tag) > 40 or not any(char.isalnum() for char in tag)
            for tag in tags
        ):
            raise serializers.ValidationError("Add 1 to 10 pronoun tags of at most 40 characters each.")
        unique_tags = []
        seen = set()
        for tag in tags:
            normalized = tag.casefold()
            if normalized not in seen:
                unique_tags.append(tag)
                seen.add(normalized)
        return ", ".join(unique_tags)

    def validate_short_bio(self, value):
        value = sanitize_multiline(value)
        if len(value) < 10:
            raise serializers.ValidationError(
                "Short bio must contain at least one short sentence."
            )
        return value

    def validate_message_to_editors(self, value):
        return sanitize_multiline(value)

    def validate_published_where(self, value):
        return sanitize_multiline(value)

    def validate_anything_else(self, value):
        return sanitize_multiline(value)

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
        sanitized = []
        for country in value:
            country = sanitize_single_line(country).upper()
            if not is_valid_country_code(country):
                raise serializers.ValidationError(f"'{country}' is not a valid country of origin.")
            if country not in sanitized:
                sanitized.append(country)
        return ",".join(sanitized)

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
        value = sanitize_single_line(value)
        if not value:
            raise serializers.ValidationError("Enter a language.")
        return value

    def validate(self, attrs):
        request = self.context.get("request")

        text_files = []
        visuals = []
        text_links = []
        visual_links = []
        video_links = []
        other_links = []
        named_links = []
        if request:
            allowed_fields = {
                name for name, field in self.fields.items() if not field.read_only
            } | {"text_files", "visuals", "text_links", "visual_links", "video_links", "other_links", "named_links"}
            unknown_fields = set(request.data) - allowed_fields
            if unknown_fields:
                raise serializers.ValidationError("Unknown submission fields were provided.")
            text_files = request.FILES.getlist("text_files")
            visuals = request.FILES.getlist("visuals")
            for field_name, links in (("text_links", text_links), ("visual_links", visual_links), ("video_links", video_links), ("other_links", other_links)):
                if self.instance is not None and field_name in request.data:
                    raise serializers.ValidationError({field_name: "Links cannot be changed here."})
                for url in submitted_links(request.data, field_name):
                    try:
                        links.append(validate_link_url(url))
                    except serializers.ValidationError as error:
                        raise serializers.ValidationError({field_name: error.detail}) from error

            if "named_links" in request.data:
                if self.instance is not None:
                    raise serializers.ValidationError({"named_links": "Links cannot be changed here."})
                raw_links = request.data["named_links"]
                if isinstance(raw_links, str):
                    try:
                        raw_links = json.loads(raw_links)
                    except ValueError as error:
                        raise serializers.ValidationError({"named_links": "Enter a list of links."}) from error
                if not isinstance(raw_links, list) or len(raw_links) > 20:
                    raise serializers.ValidationError({"named_links": "Add at most 20 links."})
                for item in raw_links:
                    if not isinstance(item, dict) or set(item) != {"name", "url"} or not isinstance(item["name"], str):
                        raise serializers.ValidationError({"named_links": "Give each link a name and URL."})
                    name = sanitize_single_line(item["name"])
                    if not name or len(name) > 120:
                        raise serializers.ValidationError({"named_links": "Give each link a name of at most 120 characters."})
                    try:
                        url = validate_link_url(item["url"])
                    except serializers.ValidationError as error:
                        raise serializers.ValidationError({"named_links": error.detail}) from error
                    named_links.append({"name": name, "url": url})

        self.validated_named_links = named_links

        self.validated_links = {
            SubmissionLink.LinkType.TEXT: text_links,
            SubmissionLink.LinkType.VISUAL: visual_links,
            SubmissionLink.LinkType.VIDEO: video_links,
            SubmissionLink.LinkType.OTHER: other_links,
        }

        if len(text_files) + len(text_links) > settings.SUBMISSION_MAX_TEXT_FILES:
            field = "text_links" if text_links else "text_files"
            raise serializers.ValidationError({field: "Too many text files or links."})
        if len(visuals) + len(visual_links) + len(video_links) > settings.SUBMISSION_MAX_VISUAL_FILES:
            field = "video_links" if video_links else "visual_links" if visual_links else "visuals"
            raise serializers.ValidationError({field: "Too many visual or video files or links."})
        if len(other_links) + len(named_links) > 20:
            raise serializers.ValidationError({"named_links": "Add at most 20 links."})

        file_limit = settings.SUBMISSION_MAX_FILE_BYTES
        total_limit = settings.SUBMISSION_MAX_TOTAL_FILES_BYTES
        for field, files in (("text_files", text_files), ("visuals", visuals)):
            for uploaded_file in files:
                if uploaded_file.size > file_limit:
                    raise serializers.ValidationError({
                        field: (
                            f"Each file must be at most {file_limit // (1024 * 1024)} MiB."
                        )
                    })
                validate_upload(uploaded_file, field)

        if sum(uploaded_file.size for uploaded_file in text_files + visuals) > total_limit:
            raise serializers.ValidationError(
                f"Files must total at most {total_limit // (1024 * 1024)} MiB."
            )

        # A new submission needs at least one file or link.
        if self.instance is None and not any((text_files, visuals, text_links, visual_links, video_links, other_links, named_links)):
            raise serializers.ValidationError(
                "A submission must include a file or link."
            )

        published_elsewhere = attrs.get(
            "published_elsewhere",
            self.instance.published_elsewhere if self.instance else None,
        )
        published_where = attrs.get(
            "published_where",
            self.instance.published_where if self.instance else "",
        )
        if published_elsewhere is True and not published_where:
            raise serializers.ValidationError({"published_where": "Tell us where this piece was published."})
        if published_elsewhere is False:
            attrs["published_where"] = ""

        return attrs
