import logging

from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from submissions.api.email import send_submission_receipt
from submissions.api.throttles import SubmissionCreateThrottle
from submissions.models import SubmissionDocument, SubmissionVote, Tag
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
        if self.action == "create":
            return [permissions.AllowAny()]
        return super().get_permissions()

    def get_throttles(self):
        if self.action == "create":
            return [SubmissionCreateThrottle()]
        return super().get_throttles()

    def get_queryset(self):
        return self.submission_repository.list().prefetch_related("documents").annotate(
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
            submission = self.submission_repository.create(serializer.validated_data)

            for text_file in request.FILES.getlist("text_files"):
                self.document_repository.create_text_document(
                    submission=submission,
                    uploaded_file=text_file,
                )

            for image in request.FILES.getlist("visuals"):
                self.document_repository.create_visual_document(
                    submission=submission,
                    uploaded_file=image,
                )

        try:
            send_submission_receipt(submission)
        except Exception:
            logger.exception(
                "Failed to send submission receipt for submission %s",
                submission.pk,
            )

        output_serializer = self.get_serializer(submission)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

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
        stored_files = {
            document.file.name: document.file.storage
            for document in instance.documents.all()
            if document.file.name
        }
        instance.delete()

        for name, storage in stored_files.items():
            if SubmissionDocument.objects.filter(file=name).exists():
                continue
            try:
                storage.delete(name)
            except Exception:
                logger.exception("Failed to delete file %s for submission %s", name, submission_id)
