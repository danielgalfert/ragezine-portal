import logging

from django.db import transaction
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response

from submissions.api.email import send_submission_emails
from submissions.repositories import SubmissionDocumentRepository, SubmissionRepository
from submissions.serializers import SubmissionSerializer


logger = logging.getLogger(__name__)


class SubmissionViewSet(viewsets.ModelViewSet):
    serializer_class = SubmissionSerializer
    permission_classes = [permissions.IsAdminUser]
    submission_repository = SubmissionRepository()
    document_repository = SubmissionDocumentRepository()

    def get_permissions(self):
        if self.action == "create":
            return [permissions.AllowAny()]
        return super().get_permissions()

    def get_queryset(self):
        return self.submission_repository.list()

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        serializer = self.get_serializer(data=data)
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
            send_submission_emails(submission)
        except Exception:
            logger.exception(
                "Failed to send submission emails for submission %s",
                submission.pk,
            )

        output_serializer = self.get_serializer(submission)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)
