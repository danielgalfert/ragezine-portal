import logging
import json
import re
from types import SimpleNamespace
from uuid import uuid4

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils.datastructures import MultiValueDict
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from submissions.api.email import send_batch_receipt, send_submission_receipt
from submissions.api.permissions import CanDeleteSubmission
from submissions.api.throttles import SubmissionCreateThrottle
from submissions.models import Artist, Submission, SubmissionDocument, SubmissionLink, SubmissionVote, Tag, Work
from submissions.repositories import SubmissionDocumentRepository, SubmissionRepository
from submissions.serializers import (
    SubmissionCommentSerializer,
    SubmissionSerializer,
    SubmissionVoteInputSerializer,
    SubmissionVoteSerializer,
    TagNameSerializer,
    TagSerializer,
)


logger = logging.getLogger(__name__)
MAX_TAGS_PER_SUBMISSION = 20
MAX_PIECES_PER_BATCH = 10
ARTIST_FIELDS = {
    "artist_name", "pronouns", "email", "country_origin",
    "countries_residence", "short_bio", "socials", "message_to_editors",
    "submitted_before", "featured_before",
}
PIECE_FIELDS = {
    "submission_type", "title", "description", "year", "language",
    "text_links", "visual_links", "video_links", "other_links", "named_links",
    "published_elsewhere", "published_where", "anything_else",
}
FILE_FIELD_PATTERN = re.compile(r"^submission_(\d+)_(text_files|visuals)$")


def _create_submission(data, repository, batch_id=None):
    # Public fields do not prove identity. Each request gets its own record.
    artist = Artist.objects.create(**{
        field: data[field] for field in ARTIST_FIELDS if field in data
    })
    submission_data = {**data, "artist": artist}
    if batch_id is not None:
        submission_data["batch_id"] = batch_id
        submission_data["batch_position"] = None
    return repository.create(submission_data)


class TagListView(generics.ListAPIView):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = TagSerializer
    queryset = Tag.objects.all()


class SubmissionViewSet(viewsets.ModelViewSet):
    serializer_class = SubmissionSerializer
    permission_classes = [permissions.IsAdminUser]
    submission_repository = SubmissionRepository()
    document_repository = SubmissionDocumentRepository()

    def get_permissions(self):
        if self.action in {"create", "create_batch"}:
            return [permissions.AllowAny()]
        if self.action == "destroy":
            return [CanDeleteSubmission()]
        return super().get_permissions()

    def get_throttles(self):
        if self.action in {"create", "create_batch"}:
            return [SubmissionCreateThrottle()]
        return super().get_throttles()

    def get_queryset(self):
        return self.submission_repository.list().select_related("artist").prefetch_related("documents", "links", "staff_comments", "works__documents", "works__links").annotate(
            yes_vote_count=Count(
                "votes", filter=Q(votes__choice=SubmissionVote.Choice.YES)
            ),
            no_vote_count=Count(
                "votes", filter=Q(votes__choice=SubmissionVote.Choice.NO)
            ),
            see_comment_vote_count=Count(
                "votes", filter=Q(votes__choice=SubmissionVote.Choice.SEE_COMMENT)
            ),
        )

    @action(detail=True, methods=["post"], url_path="tags")
    def add_tag(self, request, pk=None):
        submission = self.get_object()
        serializer = TagNameSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        name = serializer.validated_data["name"]

        existing = submission.tags.filter(name=name).first()
        if existing:
            return Response(TagSerializer(existing).data)
        if submission.tags.count() >= MAX_TAGS_PER_SUBMISSION:
            return Response(
                {"name": ["A submission can have at most 20 tags."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tag, _ = Tag.objects.get_or_create(name=name)
        submission.tags.add(tag)
        return Response(TagSerializer(tag).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"], url_path=r"tags/(?P<tag_id>[0-9]+)")
    def remove_tag(self, request, pk=None, tag_id=None):
        submission = self.get_object()
        tag = get_object_or_404(submission.tags, pk=tag_id)
        submission.tags.remove(tag)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            submission = _create_submission(
                serializer.validated_data, self.submission_repository
            )
            work = Work.objects.create(
                submission=submission, position=1,
                **{field: serializer.validated_data[field] for field in PIECE_FIELDS if field in serializer.validated_data and field not in {"text_links", "visual_links", "video_links", "other_links", "named_links"}},
            )

            for text_file in request.FILES.getlist("text_files"):
                self.document_repository.create_text_document(
                    submission=submission,
                    uploaded_file=text_file,
                    work=work,
                )

            for image in request.FILES.getlist("visuals"):
                self.document_repository.create_visual_document(
                    submission=submission,
                    uploaded_file=image,
                    work=work,
                )

            for link_type, urls in serializer.validated_links.items():
                SubmissionLink.objects.bulk_create([
                    SubmissionLink(submission=submission, work=work, link_type=link_type, url=url)
                    for url in urls
                ])
            SubmissionLink.objects.bulk_create([
                SubmissionLink(submission=submission, work=work, link_type=SubmissionLink.LinkType.OTHER, **link)
                for link in serializer.validated_named_links
            ])
        try:
            send_submission_receipt(submission)
        except Exception:
            logger.exception(
                "Failed to send submission receipt for submission %s",
                submission.pk,
            )

        output_serializer = self.get_serializer(submission)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="batch")
    def create_batch(self, request):
        try:
            artist = json.loads(request.data.get("artist", ""))
            pieces = json.loads(request.data.get("submissions", ""))
        except (TypeError, ValueError) as error:
            raise ValidationError("Send artist and submissions as JSON.") from error

        if not isinstance(artist, dict) or set(artist) - ARTIST_FIELDS:
            raise ValidationError({"artist": "Invalid artist information."})
        if not isinstance(pieces, list) or not 1 <= len(pieces) <= MAX_PIECES_PER_BATCH:
            raise ValidationError({"submissions": "Add 1 to 10 submissions."})
        if not isinstance(artist.get("submitted_before"), bool) or not isinstance(artist.get("featured_before"), bool):
            raise ValidationError({"artist": "Answer both RAGE Zine history questions."})

        for name in request.FILES:
            match = FILE_FIELD_PATTERN.fullmatch(name)
            if not match or int(match.group(1)) >= len(pieces):
                raise ValidationError({"files": "Unexpected upload field."})

        prepared = []
        total_bytes = 0
        total_files = 0
        for index, piece in enumerate(pieces):
            if not isinstance(piece, dict) or set(piece) - PIECE_FIELDS:
                raise ValidationError({"submissions": {index: "Invalid submission fields."}})
            if not isinstance(piece.get("published_elsewhere"), bool):
                raise ValidationError({"submissions": {index: "Answer the publication question."}})

            files = MultiValueDict({
                "text_files": request.FILES.getlist(f"submission_{index}_text_files"),
                "visuals": request.FILES.getlist(f"submission_{index}_visuals"),
            })
            total_bytes += sum(upload.size for _, uploads in files.lists() for upload in uploads)
            total_files += sum(len(uploads) for _, uploads in files.lists())
            data = {**artist, **piece}
            validation_request = SimpleNamespace(data=data, FILES=files)
            serializer = self.get_serializer(data=data, context={"request": validation_request})
            if not serializer.is_valid():
                raise ValidationError({"submissions": {index: serializer.errors}})
            prepared.append((serializer, files))

        if total_bytes > settings.SUBMISSION_MAX_TOTAL_FILES_BYTES:
            raise ValidationError({"files": "Uploads exceed the total size limit."})
        if total_files > 60:
            raise ValidationError({"files": "Add at most 60 files in one submission."})

        batch_id = uuid4()
        works = []
        stored_documents = []
        try:
            with transaction.atomic():
                artist_data = prepared[0][0].validated_data
                submission = _create_submission(
                    artist_data, self.submission_repository, batch_id=batch_id
                )
                for index, (serializer, files) in enumerate(prepared):
                    work = Work.objects.create(
                        submission=submission, position=index + 1,
                        **{field: serializer.validated_data[field] for field in PIECE_FIELDS if field in serializer.validated_data and field not in {"text_links", "visual_links", "video_links", "other_links", "named_links"}},
                    )
                    works.append(work)
                    for uploaded_file in files.getlist("text_files"):
                        stored_documents.append(self.document_repository.create_text_document(submission, uploaded_file, work=work))
                    for uploaded_file in files.getlist("visuals"):
                        stored_documents.append(self.document_repository.create_visual_document(submission, uploaded_file, work=work))
                    for link_type, urls in serializer.validated_links.items():
                        SubmissionLink.objects.bulk_create([
                            SubmissionLink(submission=submission, work=work, link_type=link_type, url=url)
                            for url in urls
                        ])
                    SubmissionLink.objects.bulk_create([
                        SubmissionLink(submission=submission, work=work, link_type=SubmissionLink.LinkType.OTHER, **link)
                        for link in serializer.validated_named_links
                    ])
        except Exception:
            for document in stored_documents:
                try:
                    document.file.delete(save=False)
                except Exception:
                    logger.exception("Could not remove a file after batch creation failed.")
            raise

        try:
            send_batch_receipt(submission, works)
        except Exception:
            logger.exception("Failed to send receipt for submission batch %s", batch_id)

        return Response({
            "batch_id": str(submission.batch_id) if submission.batch_id else None,
            "submission": self.get_serializer(submission).data,
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get", "post"])
    def comments(self, request, pk=None):
        submission = self.get_object()
        if request.method == "GET":
            comments = submission.staff_comments.all()
            return Response(SubmissionCommentSerializer(comments, many=True).data)

        serializer = SubmissionCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = serializer.save(
            submission=submission,
            author=request.user,
            author_name=request.user.get_username(),
        )
        return Response(
            SubmissionCommentSerializer(comment).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get", "post", "delete"])
    def votes(self, request, pk=None):
        submission = self.get_object()
        if request.method == "GET":
            return Response(self._vote_state(submission, request.user))
        if request.method == "DELETE":
            SubmissionVote.objects.filter(
                submission=submission,
                voter=request.user,
            ).delete()
            return Response(self._vote_state(submission, request.user))

        serializer = SubmissionVoteInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        choice = serializer.validated_data["choice"]
        with transaction.atomic():
            vote, created = SubmissionVote.objects.select_for_update().get_or_create(
                submission=submission,
                voter=request.user,
                defaults={"choice": choice},
            )
            if not created and vote.choice != choice:
                vote.choice = choice
                vote.save(update_fields=["choice", "updated_at"])

        return Response(
            self._vote_state(submission, request.user),
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @staticmethod
    def _vote_state(submission, user):
        votes = list(
            submission.votes.filter(choice__in=SubmissionVote.Choice.values)
            .select_related("voter")
        )
        counts = {choice: 0 for choice in SubmissionVote.Choice.values}
        for vote in votes:
            counts[vote.choice] += 1
        counts["total"] = len(votes)
        return {
            "counts": counts,
            "votes": SubmissionVoteSerializer(votes, many=True).data,
            "my_vote": next(
                (SubmissionVoteSerializer(vote).data for vote in votes if vote.voter_id == user.pk),
                None,
            ),
        }

    def perform_destroy(self, instance):
        submission_id = instance.pk
        artist_id = instance.artist_id
        stored_files = {
            document.file.name: document.file.storage
            for document in instance.documents.all()
            if document.file.name
        }
        instance.delete()
        if artist_id and not self.submission_repository.list().filter(artist_id=artist_id).exists():
            Artist.objects.filter(pk=artist_id).delete()

        for name, storage in stored_files.items():
            if SubmissionDocument.objects.filter(file=name).exists():
                continue
            try:
                storage.delete(name)
            except Exception:
                logger.exception("Failed to delete file %s for submission %s", name, submission_id)
