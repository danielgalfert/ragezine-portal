import logging

from rest_framework import status, viewsets
from rest_framework.response import Response

from submissions.api.email import send_submission_emails
from submissions.models import Submission, SubmissionText, SubmissionVisual
from submissions.serializers import SubmissionSerializer
from submissions.utils import sanitize_uploaded_filename


logger = logging.getLogger(__name__)


class SubmissionViewSet(viewsets.ModelViewSet):
    queryset = Submission.objects.all()
    serializer_class = SubmissionSerializer

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        submission = serializer.save()

        for text_file in request.FILES.getlist("text_files"):
            text_file = sanitize_uploaded_filename(text_file)
            SubmissionText.objects.create(
                submission=submission,
                file=text_file,
            )

        for image in request.FILES.getlist("visuals"):
            image = sanitize_uploaded_filename(image)
            SubmissionVisual.objects.create(
                submission=submission,
                image=image,
            )

        try:
            send_submission_emails(submission)
        except Exception:
            logger.exception("Failed to send submission emails for submission %s", submission.pk)

        output_serializer = self.get_serializer(submission)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)
