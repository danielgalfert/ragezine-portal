import logging

from django.db import transaction
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response

from submissions.api.email import send_submission_receipt
from submissions.api.throttles import SubmissionCreateThrottle
from submissions.models import SubmissionDocument
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

    def get_throttles(self):
        if self.action == "create":
            return [SubmissionCreateThrottle()]
        return super().get_throttles()

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
            send_submission_receipt(submission)
        except Exception:
            logger.exception(
                "Failed to send submission receipt for submission %s",
                submission.pk,
            )

        output_serializer = self.get_serializer(submission)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

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
