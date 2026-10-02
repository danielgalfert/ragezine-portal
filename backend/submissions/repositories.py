from submissions.models import Submission, SubmissionDocument
from submissions.utils import sanitize_uploaded_filename


class SubmissionRepository:
    def queryset(self):
        return Submission.objects.all()

    def list(self):
        return self.queryset()

    def list_with_documents(self):
        return self.queryset().prefetch_related("documents")

    def get_with_documents(self, submission_id):
        return self.list_with_documents().get(pk=submission_id)

    def create(self, validated_data):
        return Submission.objects.create(**validated_data)


class SubmissionDocumentRepository:
    def list_for_submission(self, submission):
        return submission.documents.all()

    def create(self, submission, uploaded_file, document_type):
        uploaded_file = sanitize_uploaded_filename(uploaded_file)
        return SubmissionDocument.create_from_upload(
            submission=submission,
            uploaded_file=uploaded_file,
            document_type=document_type,
        )

    def create_text_document(self, submission, uploaded_file):
        return self.create(
            submission=submission,
            uploaded_file=uploaded_file,
            document_type=SubmissionDocument.DocumentType.TEXT,
        )

    def create_visual_document(self, submission, uploaded_file):
        return self.create(
            submission=submission,
            uploaded_file=uploaded_file,
            document_type=SubmissionDocument.DocumentType.VISUAL,
        )
